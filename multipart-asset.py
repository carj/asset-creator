#!/usr/bin/python3.6

import configparser
import datetime
import uuid
import os
import hashlib
import shutil
import requests
import boto3
from xml.etree.ElementTree import Element, SubElement
from xml.etree.ElementTree import ElementTree
from xml.etree import ElementTree
from xml.dom import minidom
from os import listdir
from os.path import isfile, join
from shutil import copyfile
import sys
import threading

from botocore.config import Config
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

GB = 1024 ** 3
transfer_config = TransferConfig(multipart_threshold=1 * GB)


class ProgressPercentage(object):

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def new_token(username, password, tenent, prefix):
    resp = requests.post(
        f'https://{prefix}.preservica.com/api/accesstoken/login?username={username}&password={password}&tenant={tenent}')
    if resp.status_code == 200:
        return resp.json()['token']
    else:
        print(f"new_token failed with error code: {resp.status_code}")
        print(resp.request.url)
        raise SystemExit


def main():
    config = configparser.ConfigParser()
    config.read('asset.properties')

    asset_name = config['AssetSection']['asset.Title']
    asset_description = config['AssetSection']['asset.Description']
    asset_tag = config['AssetSection']['asset.SecurityTag']
    asset_parent = config['AssetSection']['asset.Parent']

    if not asset_name:
        print("Title is not defined")
        raise SystemExit

    if not asset_description:
        print("Description is not defined")
        raise SystemExit

    if not asset_tag:
        print("Security Tag is not defined")
        raise SystemExit

    if not asset_parent:
        print("Parent folder is not defined")
        raise SystemExit

    xip = Element('XIP')
    xip.set('xmlns', 'http://preservica.com/XIP/v6.0')
    io = SubElement(xip, 'InformationObject')

    ref = SubElement(io, 'Ref')
    ref.text = str(uuid.uuid4())
    asset_id = ref.text
    title = SubElement(io, 'Title')
    title.text = asset_name
    description = SubElement(io, 'Description')
    description.text = asset_description
    security = SubElement(io, 'SecurityTag')
    security.text = asset_tag
    custom_type = SubElement(io, 'CustomType')
    custom_type.text = ""
    parent = SubElement(io, 'Parent')
    parent.text = asset_parent

    preservation_files_path = config['AssetSection']['preservation.files.folder']
    access_files_path = config['OptionalRepresentationsSection']['access.files.folder']

    access_content_description = config['OptionalSection']['access.content.object.description']
    preservation_content_description = config['OptionalSection']['preservation.content.object.description']
    access_generation_label = config['OptionalSection']['access.generation.label']
    preservation_generation_label = config['OptionalSection']['preservation.generation.label']

    if not preservation_files_path:
        print("Preservation file list has not been set")
        raise SystemExit

    export_folder = config['AssetSection']['asset.export.folder']
    if not export_folder:
        print("Export location has not been set")
        raise SystemExit

    access_refs_dict = {}
    if access_files_path:
        access_refs_dict = make_representation(xip, "Access", "Access", access_files_path, asset_id)

    preservation_refs_dict = {}
    if preservation_files_path:
        preservation_refs_dict = make_representation(xip, "Preservation", "Preservation", preservation_files_path,
                                                     asset_id)
    if access_refs_dict:
        make_content_objects(xip, access_refs_dict, asset_id, asset_tag, access_content_description, "")

    if preservation_refs_dict:
        make_content_objects(xip, preservation_refs_dict, asset_id, asset_tag, preservation_content_description, "")

    if access_refs_dict:
        make_generation(xip, access_refs_dict, access_generation_label)

    if preservation_refs_dict:
        make_generation(xip, preservation_refs_dict, preservation_generation_label)

    if access_refs_dict:
        make_bitstream(xip, access_refs_dict, access_files_path)

    if preservation_refs_dict:
        make_bitstream(xip, preservation_refs_dict, preservation_files_path)

    identifier_key = config['OptionalAssetIdentifierSection']['asset.identifier.key']
    identifier_value = config['OptionalAssetIdentifierSection']['asset.identifier.value']

    if identifier_key:
        if identifier_value:
            identifier = SubElement(xip, 'Identifier')
            id_type = SubElement(identifier, "Type")
            id_type.text = identifier_key
            id_value = SubElement(identifier, "Value")
            id_value.text = identifier_value
            id_io = SubElement(identifier, "Entity")
            id_io.text = asset_id

    metadata_path = config['OptionalAssetMetadataSection']['asset.metadata.xmlfile']
    metadata_ns = config['OptionalAssetMetadataSection']['asset.metadata.namespace']

    if metadata_ns:
        if metadata_path:
            if os.path.exists(metadata_path) and os.path.isfile(metadata_path):
                descriptive_metadata = ElementTree.parse(metadata_path)
                metadata = SubElement(xip, 'Metadata', {'schemaUri': metadata_ns})
                metadata_ref = SubElement(metadata, 'Ref')
                metadata_ref.text = str(uuid.uuid4())
                entity = SubElement(metadata, 'Entity')
                entity.text = asset_id
                content = SubElement(metadata, 'Content')
                content.append(descriptive_metadata.getroot())

    if export_folder:
        top_level_folder = os.path.join(export_folder, asset_id)
        os.mkdir(top_level_folder)
        inner_folder = os.path.join(top_level_folder, asset_id)
        os.mkdir(inner_folder)
        os.mkdir(os.path.join(inner_folder, "content"))
        metadata_path = os.path.join(inner_folder, "metadata.xml")
        metadata = open(metadata_path, "wt", encoding='utf-8')
        metadata.write(prettify(xip))
        metadata.close()
        if access_refs_dict:
            for filename, ref in access_refs_dict.items():
                src_file = os.path.join(access_files_path, filename)
                dst_file = os.path.join(os.path.join(inner_folder, "content"), filename)
                copyfile(src_file, dst_file)
        if preservation_refs_dict:
            for filename, ref in preservation_refs_dict.items():
                src_file = os.path.join(preservation_files_path, filename)
                dst_file = os.path.join(os.path.join(inner_folder, "content"), filename)
                copyfile(src_file, dst_file)
        shutil.make_archive(top_level_folder, 'zip', top_level_folder)
        shutil.rmtree(top_level_folder)

    user_domain = config['OptionalAPIUploadSection']['user.domain']
    user_name = config['OptionalAPIUploadSection']['user.username']
    user_password = config['OptionalAPIUploadSection']['user.password']
    user_tenant = config['OptionalAPIUploadSection']['user.tenant']

    if user_domain and user_name and user_password and user_tenant:
        token = new_token(user_name, user_password, user_tenant, user_domain)
        bucket = f'{user_tenant.lower()}.package.upload'
        endpoint = f'https://{user_domain}.preservica.com/api/s3/buckets'
        print(f'Uploading to Preservica: using s3 bucket {bucket}')
        client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=token, aws_secret_access_key="NOT_USED",
                              config=Config(s3={'addressing_style': 'path'}))
        sip_name = os.path.join(export_folder, asset_id + ".zip")
        metadata = {'Metadata': {'structuralobjectreference': asset_parent}}
        if os.path.exists(sip_name) and os.path.isfile(sip_name):
            try:
                response = client.upload_file(sip_name, bucket, asset_id + ".zip", ExtraArgs=metadata,
                                              Callback=ProgressPercentage(sip_name), Config=transfer_config)
            except ClientError as e:
                print(e)


def make_bitstream(xip, refs_dict, root_path):
    for filename, ref in refs_dict.items():
        bitstream = SubElement(xip, 'Bitstream')
        filenameElement = SubElement(bitstream, "Filename")
        filenameElement.text = filename
        filesize = SubElement(bitstream, "FileSize")
        fullPath = os.path.join(root_path, filename)
        file_stats = os.stat(fullPath)
        filesize.text = str(file_stats.st_size)
        fixities = SubElement(bitstream, "Fixities")
        fixity = SubElement(fixities, "Fixity")
        fixityAlgorithmRef = SubElement(fixity, "FixityAlgorithmRef")
        fixityAlgorithmRef.text = "SHA1"
        fixityValue = SubElement(fixity, "FixityValue")
        sha1 = hashlib.sha1()
        BLOCKSIZE = 65536
        with open(fullPath, 'rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                sha1.update(buf)
                buf = afile.read(BLOCKSIZE)
        fixityValue.text = sha1.hexdigest()


def make_generation(xip, refs_dict, generation_label):
    for filename, ref in refs_dict.items():
        generation = SubElement(xip, 'Generation', {"original": "true", "active": "true"})
        content_object = SubElement(generation, "ContentObject")
        content_object.text = ref
        label = SubElement(generation, "Label")
        if generation_label:
            label.text = generation_label
        else:
            label.text = os.path.splitext(filename)[0]
        effective_date = SubElement(generation, "EffectiveDate")
        effective_date.text = datetime.datetime.now().isoformat()
        bitstreams = SubElement(generation, "Bitstreams")
        bitstream = SubElement(bitstreams, "Bitstream")
        bitstream.text = filename
        SubElement(generation, "Formats")
        SubElement(generation, "Properties")


def make_content_objects(xip, refs_dict, io_ref, tag, content_description, content_type):
    for filename, ref in refs_dict.items():
        content_object = SubElement(xip, 'ContentObject')
        ref_element = SubElement(content_object, "Ref")
        ref_element.text = ref
        title = SubElement(content_object, "Title")
        title.text = os.path.splitext(filename)[0]
        description = SubElement(content_object, "Description")
        description.text = content_description
        security_tag = SubElement(content_object, "SecurityTag")
        security_tag.text = tag
        custom_type = SubElement(content_object, "CustomType")
        custom_type.text = content_type
        parent = SubElement(content_object, "Parent")
        parent.text = io_ref


def make_representation(xip, rep_name, rep_type, path, io_ref):
    representation = SubElement(xip, 'Representation')
    io_link = SubElement(representation, 'InformationObject')
    io_link.text = io_ref
    access_name = SubElement(representation, 'Name')
    access_name.text = rep_name
    access_type = SubElement(representation, 'Type')
    access_type.text = rep_type
    content_objects = SubElement(representation, 'ContentObjects')
    rep_files = [f for f in listdir(path) if isfile(join(path, f))]
    refs_dict = {}
    for f in rep_files:
        content_object = SubElement(content_objects, 'ContentObject')
        content_object_ref = str(uuid.uuid4())
        content_object.text = content_object_ref
        refs_dict[f] = content_object_ref
    return refs_dict


main()

#!/usr/bin/python3.6

import configparser
import datetime
import uuid
import os
import hashlib
import shutil
from xml.etree.ElementTree import Element, SubElement
from xml.etree.ElementTree import ElementTree
from xml.etree import ElementTree
from xml.dom import minidom
from os import listdir
from os.path import isfile, join
from shutil import copyfile


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


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
        access_refs_dict = make_representation(xip, "Access", "Access", access_files_path, ref.text)

    preservation_refs_dict = {}
    if preservation_files_path:
        preservation_refs_dict = make_representation(xip, "Preservation", "Preservation", preservation_files_path,
                                                     ref.text)
    if access_refs_dict:
        make_content_objects(xip, access_refs_dict, ref.text, asset_tag, access_content_description, "")

    if preservation_refs_dict:
        make_content_objects(xip, preservation_refs_dict, ref.text, asset_tag, preservation_content_description, "")

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
            id_io.text = ref.text

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
                entity.text = ref.text
                content = SubElement(metadata, 'Content')
                content.append(descriptive_metadata.getroot())

    if export_folder:
        top_level_folder = os.path.join(export_folder, ref.text)
        os.mkdir(top_level_folder)
        inner_folder = os.path.join(top_level_folder, ref.text)
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

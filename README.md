# asset-creator
Create multi-part Preservica assets.

Creates a ZIP format submission containing 1 Preservica multi-part asset.

Assets are made from a folder containing a set of preservation files and an optional second folder containing access files.

The python script is controlled by a properties file containing the asset attributes

```
[AssetSection]
asset.Title=
asset.Description=
asset.SecurityTag=
asset.Parent=
preservation.files.folder=
asset.export.folder=


[OptionalRepresentationsSection]
access.files.folder=

[OptionalSection]
preservation.content.object.description=
access.content.object.description=
preservation.generation.label=
access.generation.label=


[OptionalAssetMetadataSection]
asset.metadata.namespace=
asset.metadata.xmlfile=

[OptionalAssetIdentifierSection]
asset.identifier.key=
asset.identifier.value=
```

For example:

The Title of the asset as shown in Explorer
```
asset.Title=Adventures of Huckleberry Finn
```
The Description of the asset as shown in Explorer
```
asset.Description=A novel by Mark Twain, first published in the United Kingdom in December 1884.
```
The SecurityTag of the asset
```
asset.SecurityTag=open
```
The reference of the parent folder in Explorer
```
asset.Parent=992ce1b2-9ccc-4a66-ad38-7f86526e146b
```
A folder containing the preservation files which make up the the preservation representation of the nmulti-file asset 
```
preservation.files.folder=/mnt/books/Twain/Finn/Tiffs/
```
A folder where the complete SIP is export to
```
asset.export.folder=/mnt/sips/export
```
A folder containing the access files which make up the access representation of the multi-file asset 
```
access.files.folder=/mnt/books/Twain/Finn/PDFs/
```
An optional label on the preservation content objects
```
preservation.content.object=Scanned TIFF Images
```
An optional label on the access content objects, only used if the access representation is specfied
```
access.content.object.description=Scanned JPG Images
```
An optional label on the preservation generation
```
preservation.generation.label=
```
An optional label on the access generation
```
access.generation.label=
```
The namespace of any optional descriptive metadata attached to the asset
```
asset.metadata.namespace=http://purl.org/dc/elements/1.1/
```
The path to an optional XML file containing the asset descriptive metadata
```
asset.metadata.xmlfile=/mnt/books/Twain/Finn/DublinCore.xml
```
The key for an optional asset external identifier
```
asset.identifier.key=ISBN
```
The value for an optional asset external identifier
```
asset.identifier.value= 978-3-16-148410-0
```


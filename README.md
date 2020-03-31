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

The Title of the asset as shown in Explorer
```
asset.Title=
```
The Description of the asset as shown in Explorer
```
asset.Description=
```
The SecurityTag of the asset
```
asset.SecurityTag=
```
The reference of the parent folder in Explorer
```
asset.Parent=
```
A folder containing the preservation files which make up the multi-file asset 
```
preservation.files.folder=
```


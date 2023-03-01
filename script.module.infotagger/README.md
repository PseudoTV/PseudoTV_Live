# script.module.infotagger
The InfoTagger module is a wrapper for new Nexus InfoTagVideo ListItem methods to maintain backwards compatibility with old ListItem.setInfo() style methods


Usage

Import as a dependency in `addon.xml`
```xml
<requires>
    <import addon="script.module.infotagger" version="0.0.3" />
</requires>
 ```
 
When making your ListItem 

 ```python
 from infotagger.listitem import ListItemInfoTag

# Make your listitem as normal
li = xbmcgui.ListItem()

# Pass listitem to the infotagger module and specify tag type
info_tag = ListItemInfoTag(li, 'video')

# li.setInfo(infolabels)
info_tag.set_info(infolabels)

# li.setUniqueIDs(unique_ids)
info_tag.set_unique_ids(unique_ids)

# li.setCast(cast)
info_tag.set_cast(cast)

# li.addStreamInfo('video', videostream_values)
info_tag.add_stream_info('video', videostream_values)
 ```
 
 
Optional alternative for setting all video/audio/subtitle streams using a single dictionary (e.g. as returned by JSON RPC).

```python
"""
stream_details = {
        'video': [{videostream_1_values}, {videostream_2_values} ...],
        'audio': [{audiostream_1_values}, {audiostream_2_values} ...],
        'subtitle': [{subtitlestream_1_values}, {subtitlestream_2_values} ...]}
"""
info_tag.set_stream_details(stream_details)
```


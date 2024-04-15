#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

'''
Code by Alba Mendez, manually copied and pasted, had 8 revisions when copied.
https://gist.github.com/mildsunrise/ffd74730504e4dc44f47fc7528e7bf59

Portable* ISO Base Media File Format dissector / parser.
(*) Needs Python 3.8+

Goals / development guidelines:

  - Low level. Meant as a dissector, i.e. to obtain info about the structure of the file
    rather than high level info.

  - Print offsets to every box to let users inspect deeper. If parsing fails, print an
    error for that particular box followed by a hexdump.

  - Don't parse non-MP4 structures. It is fine to parse the info in the MP4 boxes,
    as long as this info is specific to MP4. Examples of things we don't parse:
     - Codec-specific structures (SPS, PPS)
     - ID3v2 blobs
     - H.264 NALUs
     - XML
     - ICC profiles
    These blobs are just left as hexdump, with their offsets / length printed in case the
    user wants to dive deeper.
    The only exception is when this info is needed to dissect other MP4 boxes correctly.

  - Focus on dissection, not parsing. First priority is to show the box structure correctly
    and to 'dig as deeper as possible' if there are nested boxes; decoding non-box info
    (instead of showing hexdumps) is second priority.

  - Print *every field on the wire*, with only minimal / mostly obvious postprocessing.
    Exception: versions / flags that are restricted to a single value.
    Exception: values which have a default (`template`) set by spec, which may be omitted
    from output if the value is set to the default, and `show_defaults` was not set.
    Exception: big boxes, or long rows of output, may be summarized through the
    `max_dump` (for hexdumps) and `max_rows` (for tables) options.

  - Option to hide lengths / offset (for i.e. diffs).

  - In the future we should have options to make the output interoperable (make it machine
    friendly like JSON), don't use global variables for config/state, allow output to a
    different file (for programmatic use).

  - Parsed fields should be named exactly like in the spec's syntax.
    Both in code, and in the output.

  - Performance isn't a concern. Correctness is more important, but it's also nice for
    the code to be 'hacker-friendly' for people who may want to tweak it.
'''

from globals import *

import itertools

durations = []
indent_n  = 4
bytes_per_line = 16
max_rows = 7
max_dump = bytes_per_line * max_rows
show_lengths = True
show_offsets = True
show_defaults = False
show_descriptions = True
colorize = False

mask = lambda n: ~((~0) << n)
get_bits = lambda x, end, start: (x & mask(end)) >> start
split_bits = lambda x, *bits: (get_bits(x, a, b) for a, b in pairwise(bits))

# UTILITIES
def metaPrint(item):
    ...
    # print(item)

def pairwise(iterable):
    try: return itertools.pairwise(iterable)
    except:
        a, b = itertools.tee(iterable)
        next(b, None)
        try:    return itertools.izip(a, b)
        except: return zip(a, b)

def unique_dict(x):
    r = {}
    for k, v in x:
        #assert k not in r, f'duplicate key {repr(k)}: existing {repr(r[k])}, got {repr(v)}'
        r[k] = v
    return r

def read_string(stream, optional=False):
    result = bytearray()
    while not MONITOR.abortRequested():
        b = stream.read(1)
        if not b:
            if optional and not result: return None
            raise EOFError('EOF while reading string')
        b = b[0]
        if not b: break
        result.append(b)
    return result.decode('utf-8')

def unpack(stream, struct_fmt: str) -> tuple:
    struct_obj = struct.Struct('>' + struct_fmt) # FIXME: caching
    return struct_obj.unpack(stream.read(struct_obj.size))

def pad_iter(iterable, size, default=None):
    iterator = iter(iterable)
    for _ in range(size):
        yield next(iterator, default)

def split_in_groups(iterable, size):
    iterator = iter(iterable)
    while not MONITOR.abortRequested() and (group := list(itertools.islice(iterator, size))):
        yield group

def ansi_sgr(p: str, content: str):
    content = str(content)
    if not colorize: return content
    if not content.endswith('\x1b[m'):
        content += '\x1b[m'
    return f'\x1b[{p}m' + content
    
ansi_bold = lambda x: ansi_sgr('1', x)
ansi_dim = lambda x: ansi_sgr('2', x)
ansi_fg0 = lambda x: ansi_sgr('30', x)
ansi_fg1 = lambda x: ansi_sgr('31', x)
ansi_fg2 = lambda x: ansi_sgr('32', x)
ansi_fg3 = lambda x: ansi_sgr('33', x)
ansi_fg4 = lambda x: ansi_sgr('34', x)
ansi_fg5 = lambda x: ansi_sgr('35', x)
ansi_fg6 = lambda x: ansi_sgr('36', x)
ansi_fg7 = lambda x: ansi_sgr('37', x)

def print_hex_dump(data: memoryview, prefix: str):
    colorize_byte = lambda x, r: \
        ansi_dim(ansi_fg2(x)) if r == 0 else \
        ansi_fg3(x) if chr(r).isascii() and chr(r).isprintable() else \
        ansi_fg2(x)
    format_hex = lambda x: colorize_byte(f'{x:02x}', x) if x != None else '  '
    format_char = lambda x: colorize_byte(x if x.isascii() and (x.isprintable() or x == ' ') else '.', ord(x))

    def format_line(line):
        groups = split_in_groups(pad_iter(line, bytes_per_line), 4)
        hex_part = '  '.join(' '.join(map(format_hex, group)) for group in groups)
        char_part = ''.join(format_char(x) for x in map(chr, line))
        return hex_part + '   ' + char_part
    for line in split_in_groups(data[:max_dump], bytes_per_line):
        metaPrint(prefix + format_line(line))
    if len(data) > max_dump:
        metaPrint(prefix + '...')

def print_error(exc, prefix: str):
    metaPrint(prefix + f'{ansi_bold(ansi_fg1("ERROR:"))} {ansi_fg1(exc)}\n')

# CORE PARSING
box_registry = [
    ({
        'name': 'ISO/IEC 14496-12',
        'title': 'Information technology — Coding of audio-visual objects — Part 12: ISO base media file format',
        'version': '2015',
        'url': 'https://www.iso.org/standard/68960.html',
    }, {
        'ftyp': ('FileTypeBox', 'Box'),
        'mdat': ('MediaDataBox', 'Box'),
        'pdin': ('ProgressiveDownloadInfoBox', 'FullBox'),
        'moov': ('MovieBox', 'Box'),
        'mvhd': ('MovieHeaderBox', 'FullBox'),
        'trak': ('TrackBox', 'Box'),
        'tkhd': ('TrackHeaderBox', 'FullBox'),
        'tref': ('TrackReferenceBox', 'Box'),
        'mdia': ('MediaBox', 'Box'),
        'mdhd': ('MediaHeaderBox', 'FullBox'),
        'hdlr': ('HandlerBox', 'FullBox'),
        'minf': ('MediaInformationBox', 'Box'),
        'nmhd': ('NullMediaHeaderBox', 'FullBox'),
        'elng': ('ExtendedLanguageBox', 'FullBox'),
        'stbl': ('SampleTableBox', 'Box'),
        'btrt': ('BitRateBox', 'Box'),
        'stsd': ('SampleDescriptionBox', 'FullBox'),
        'stdp': ('DegradationPriorityBox', 'FullBox'),
        'stts': ('TimeToSampleBox', 'FullBox'),
        'ctts': ('CompositionOffsetBox', 'FullBox'),
        'cslg': ('CompositionToDecodeBox', 'FullBox'),
        'stss': ('SyncSampleBox', 'FullBox'),
        'stsh': ('ShadowSyncSampleBox', 'FullBox'),
        'sdtp': ('SampleDependencyTypeBox', 'FullBox'),
        'edts': ('EditBox', 'Box'),
        'elst': ('EditListBox', 'FullBox'),
        'dinf': ('DataInformationBox', 'Box'),
        'url ': ('DataEntryUrlBox', 'FullBox'),
        'urn ': ('DataEntryUrnBox', 'FullBox'),
        'dref': ('DataReferenceBox', 'FullBox'),
        'stsz': ('SampleSizeBox', 'FullBox'),
        'stz2': ('CompactSampleSizeBox', 'FullBox'),
        'stsc': ('SampleToChunkBox', 'FullBox'),
        'stco': ('ChunkOffsetBox', 'FullBox'),
        'co64': ('ChunkLargeOffsetBox', 'FullBox'),
        'padb': ('PaddingBitsBox', 'FullBox'),
        'subs': ('SubSampleInformationBox', 'FullBox'),
        'saiz': ('SampleAuxiliaryInformationSizesBox', 'FullBox'),
        'saio': ('SampleAuxiliaryInformationOffsetsBox', 'FullBox'),
        'mvex': ('MovieExtendsBox', 'Box'),
        'mehd': ('MovieExtendsHeaderBox', 'FullBox'),
        'trex': ('TrackExtendsBox', 'FullBox'),
        'moof': ('MovieFragmentBox', 'Box'),
        'mfhd': ('MovieFragmentHeaderBox', 'FullBox'),
        'traf': ('TrackFragmentBox', 'Box'),
        'tfhd': ('TrackFragmentHeaderBox', 'FullBox'),
        'trun': ('TrackRunBox', 'FullBox'),
        'mfra': ('MovieFragmentRandomAccessBox', 'Box'),
        'tfra': ('TrackFragmentRandomAccessBox', 'FullBox'),
        'mfro': ('MovieFragmentRandomAccessOffsetBox', 'FullBox'),
        'tfdt': ('TrackFragmentBaseMediaDecodeTimeBox', 'FullBox'),
        'leva': ('LevelAssignmentBox', 'FullBox'),
        'trep': ('TrackExtensionPropertiesBox', 'FullBox'),
        'assp': ('AlternativeStartupSequencePropertiesBox', 'FullBox'),
        'sbgp': ('SampleToGroupBox', 'FullBox'),
        'sgpd': ('SampleGroupDescriptionBox', 'FullBox'),
        'udta': ('UserDataBox', 'Box'),
        'cprt': ('CopyrightBox', 'FullBox'),
        'tsel': ('TrackSelectionBox', 'FullBox'),
        'kind': ('KindBox', 'FullBox'),
        'meta': ('MetaBox', 'FullBox'),
        'xml ': ('XMLBox', 'FullBox'),
        'bxml': ('BinaryXMLBox', 'FullBox'),
        'iloc': ('ItemLocationBox', 'FullBox'),
        'pitm': ('PrimaryItemBox', 'FullBox'),
        'ipro': ('ItemProtectionBox', 'FullBox'),
        'fdel': ('FDItemInfoExtension', 'ItemInfoExtension'),
        'infe': ('ItemInfoEntry', 'FullBox'),
        'iinf': ('ItemInfoBox', 'FullBox'),
        'meco': ('AdditionalMetadataContainerBox', 'Box'),
        'mere': ('MetaboxRelationBox', 'FullBox'),
        'idat': ('ItemDataBox', 'Box'),
        'iref': ('ItemReferenceBox', 'FullBox'),
        'sinf': ('ProtectionSchemeInfoBox', 'Box'),
        'frma': ('OriginalFormatBox', 'Box'),
        'schm': ('SchemeTypeBox', 'FullBox'),
        'schi': ('SchemeInformationBox', 'Box'),
        'paen': ('PartitionEntry', 'Box'),
        'fiin': ('FDItemInformationBox', 'FullBox'),
        'fpar': ('FilePartitionBox', 'FullBox'),
        'fecr': ('FECReservoirBox', 'FullBox'),
        'segr': ('FDSessionGroupBox', 'Box'),
        'gitn': ('GroupIdToNameBox', 'FullBox'),
        'fire': ('FileReservoirBox', 'FullBox'),
        'strk': ('SubTrack', 'Box'),
        'stri': ('SubTrackInformation', 'FullBox'),
        'strd': ('SubTrackDefinition', 'Box'),
        'stsg': ('SubTrackSampleGroupBox', 'FullBox'),
        'rinf': ('RestrictedSchemeInfoBox', 'Box'),
        'stvi': ('StereoVideoBox', 'FullBox'),
        'sidx': ('SegmentIndexBox', 'FullBox'),
        'ssix': ('SubsegmentIndexBox', 'FullBox'),
        'prft': ('ProducerReferenceTimeBox', 'FullBox'),
        'icpv': ('IncompleteAVCSampleEntry', 'VisualSampleEntry'),
        'cinf': ('CompleteTrackInfoBox', 'Box'),
        'rtp ': ('RtpHintSampleEntry', 'SampleEntry'),
        'tims': ('timescaleentry', 'Box'),
        'tsro': ('timeoffset', 'Box'),
        'snro': ('sequenceoffset', 'Box'),
        'srtp': ('SrtpHintSampleEntry', 'SampleEntry'),
        'srpp': ('SRTPProcessBox', 'FullBox'),
        'hnti': ('moviehintinformation', 'box'),
        'rtp ': ('rtpmoviehintinformation', 'box'),
        'hnti': ('trackhintinformation', 'box'),
        'sdp ': ('rtptracksdphintinformation', 'box'),
        'hinf': ('hintstatisticsbox', 'box'),
        'trpy': ('hintBytesSent', 'box'),
        'nump': ('hintPacketsSent', 'box'),
        'tpyl': ('hintBytesSent', 'box'),
        'totl': ('hintBytesSent', 'box'),
        'npck': ('hintPacketsSent', 'box'),
        'tpay': ('hintBytesSent', 'box'),
        'maxr': ('hintmaxrate', 'box'),
        'dmed': ('hintmediaBytesSent', 'box'),
        'dimm': ('hintimmediateBytesSent', 'box'),
        'drep': ('hintrepeatedBytesSent', 'box'),
        'tmin': ('hintminrelativetime', 'box'),
        'tmax': ('hintmaxrelativetime', 'box'),
        'pmax': ('hintlargestpacket', 'box'),
        'dmax': ('hintlongestpacket', 'box'),
        'payt': ('hintpayloadID', 'box'),
        'fdp ': ('FDHintSampleEntry', 'SampleEntry'),
        'fdsa': ('FDsample', 'Box'),
        'fdpa': ('FDpacketBox', 'Box'),
        'extr': ('ExtraDataBox', 'Box'),
        'feci': ('FECInformationBox', 'Box'),
        'rm2t': ('MPEG2TSReceptionSampleEntry', 'MPEG2TSSampleEntry'),
        'sm2t': ('MPEG2TSServerSampleEntry', 'MPEG2TSSampleEntry'),
        'tPAT': ('PATBox', 'Box'),
        'tPMT': ('PMTBox', 'Box'),
        'tOD ': ('ODBox', 'Box'),
        'tsti': ('TSTimingBox', 'Box'),
        'istm': ('InitialSampleTimeBox', 'Box'),
        'pm2t': ('ProtectedMPEG2TransportStreamSampleEntry', 'MPEG2TransportStreamSampleEntry'),
        'rrtp': ('ReceivedRtpHintSampleEntry', 'SampleEntry'),
        'tssy': ('timestampsynchrony', 'Box'),
        'rssr': ('ReceivedSsrcBox', 'Box'),
        'rtpx': ('rtphdrextTLV', 'Box'),
        'rcsr': ('receivedCSRC', 'Box'),
        'rsrp': ('ReceivedSrtpHintSampleEntry', 'SampleEntry'),
        'ccid': ('ReceivedCryptoContextIdBox', 'Box'),
        'sroc': ('RolloverCounterBox', 'Box'),
        'roll': ('VisualRollRecoveryEntry', 'VisualSampleGroupEntry'),
        'roll': ('AudioRollRecoveryEntry', 'AudioSampleGroupEntry'),
        'prol': ('AudioPreRollEntry', 'AudioSampleGroupEntry'),
        'rash': ('RateShareEntry', 'SampleGroupDescriptionEntry'),
        'alst': ('AlternativeStartupEntry', 'VisualSampleGroupEntry'),
        'rap ': ('VisualRandomAccessEntry', 'VisualSampleGroupEntry'),
        'tele': ('TemporalLevelEntry', 'VisualSampleGroupEntry'),
        'sap ': ('SAPEntry', 'SampleGroupDescriptionEntry'),
        'vmhd': ('VideoMediaHeaderBox', 'FullBox'),
        'pasp': ('PixelAspectRatioBox', 'Box'),
        'clap': ('CleanApertureBox', 'Box'),
        'colr': ('ColourInformationBox', 'Box'),
        'smhd': ('SoundMediaHeaderBox', 'FullBox'),
        'srat': ('SamplingRateBox', 'FullBox'),
        'chnl': ('ChannelLayout', 'FullBox'),
        'dmix': ('DownMixInstructions', 'FullBox'),
        'tlou': ('TrackLoudnessInfo', 'LoudnessBaseBox'),
        'alou': ('AlbumLoudnessInfo', 'LoudnessBaseBox'),
        'ludt': ('LoudnessBox', 'Box'),
        'metx': ('XMLMetaDataSampleEntry', 'MetaDataSampleEntry'),
        'txtC': ('TextConfigBox', 'Fullbox'),
        'mett': ('TextMetaDataSampleEntry', 'MetaDataSampleEntry'),
        'uri ': ('URIBox', 'FullBox'),
        'uriI': ('URIInitBox', 'FullBox'),
        'urim': ('URIMetaSampleEntry', 'MetaDataSampleEntry'),
        'hmhd': ('HintMediaHeaderBox', 'FullBox'),
        'stxt': ('SimpleTextSampleEntry', 'PlainTextSampleEntry'),
        'sthd': ('SubtitleMediaHeaderBox', 'FullBox'),
        'stpp': ('XMLSubtitleSampleEntry', 'SubtitleSampleEntry'),
        'sbtt': ('TextSubtitleSampleEntry', 'SubtitleSampleEntry'),
        'free': ('FreeSpaceBox', 'Box'),
        'skip': ('FreeSpaceBox', 'Box'),
    }),
    ({
        'name': 'ISO/IEC 14496-14',
        'title': 'Information technology — Coding of audio-visual objects — Part 14: MP4 file format',
        'version': '2003',
        'url': 'https://www.iso.org/standard/38538.html',
    }, {
        'iods': ('ObjectDescriptorBox', 'FullBox'),
        'esds': ('ESDBox', 'FullBox'),
        'mp4v': ('MP4VisualSampleEntry', 'VisualSampleEntry'),
        'mp4a': ('MP4AudioSampleEntry', 'AudioSampleEntry'),
        'mp4s': ('MpegSampleEntry', 'SampleEntry'),
    }),
    ({
        'name': 'ISO/IEC 14496-15',
        'title': 'Information technology — Coding of audio-visual objects — Part 15: Carriage of network abstraction layer (NAL) unit structured video in ISO base media file format',
        'version': '2014',
        'url': 'https://www.iso.org/standard/65216.html',
    }, {
        'avcC': ('AVCConfigurationBox', 'Box'),
        'm4ds': ('MPEG4ExtensionDescriptorsBox', 'Box'),
        'avc1': ('AVCSampleEntry', 'VisualSampleEntry'),
        'avc3': ('AVCSampleEntry', 'VisualSampleEntry'),
        'avc2': ('AVC2SampleEntry', 'VisualSampleEntry'),
        'avc4': ('AVC2SampleEntry', 'VisualSampleEntry'),
        'avcp': ('AVCParameterSampleEntry', 'VisualSampleEntry'),
        'avss': ('AVCSubSequenceEntry', 'VisualSampleGroupEntry'),
        'avll': ('AVCLayerEntry', 'VisualSampleGroupEntry'),
        'svcC': ('SVCConfigurationBox', 'Box'),
        'seib': ('ScalabilityInformationSEIBox', 'Box'),
        'svcP': ('SVCPriorityAssignmentBox', 'Box'),
        'svc1': ('SVCSampleEntry', 'VisualSampleEntry'),
        'svc2': ('SVCSampleEntry', 'VisualSampleEntry'),
        'tiri': ('TierInfoBox', 'Box'),
        'tibr': ('TierBitRateBox', 'Box'),
        'svpr': ('PriorityRangeBox', 'Box'),
        'svop': ('SVCDependencyRangeBox', 'Box'),
        'svip': ('InitialParameterSetBox', 'Box'),
        'rrgn': ('RectRegionBox', 'Box'),
        'buff': ('BufferingBox', 'Box'),
        'ldep': ('TierDependencyBox', 'Box'),
        'iroi': ('IroiInfoBox', 'Box'),
        'tran': ('TranscodingInfoBox', 'Box'),
        'scif': ('ScalableGroupEntry', 'VisualSampleGroupEntry'),
        'mvif': ('MultiviewGroupEntry', 'VisualSampleGroupEntry'),
        'scnm': ('ScalableNALUMapEntry', 'VisualSampleGroupEntry'),
        'dtrt': ('DecodeRetimingEntry', 'VisualSampleGroupEntry'),
        'vipr': ('ViewPriorityBox', 'Box'),
        'vipr': ('ViewPriorityEntry', 'VisualSampleGroupEntry'),
        'sstl': ('SVCSubTrackLayerBox', 'FullBox'),
        'mstv': ('MVCSubTrackViewBox', 'FullBox'),
        'stti': ('SubTrackTierBox', 'FullBox'),
        'stmg': ('MVCSubTrackMultiviewGroupBox', 'FullBox'),
        'svmC': ('SVCMetadataSampleConfigBox', 'FullBox'),
        'qlif': ('SVCPriorityLayerInfoBox', 'Box'),
        'svcM': ('SVCMetadataSampleEntry', 'MetadataSampleEntry'),
        'icam': ('IntrinsicCameraParametersBox', 'FullBox'),
        'ecam': ('ExtrinsicCameraParametersBox', 'FullBox'),
        'vwid': ('ViewIdentifierBox', 'FullBox'),
        'mvcC': ('MVCConfigurationBox', 'Box'),
        'vsib': ('ViewScalabilityInformationSEIBox', 'Box'),
        'mvcg': ('MultiviewGroupBox', 'FullBox'),
        'swtc': ('MultiviewGroupRelationBox', 'FullBox'),
        'vwdi': ('MultiviewSceneInfoBox', 'Box'),
        'mvcP': ('MVCViewPriorityAssignmentBox', 'Box'),
        'hvcC': ('HEVCConfigurationBox', 'Box'),
        'hvc1': ('HEVCSampleEntry', 'VisualSampleEntry'),
        'hev1': ('HEVCSampleEntry', 'VisualSampleEntry'),
        'sync': ('SyncSampleEntry', 'VisualSampleGroupEntry'),
        'tscl': ('TemporalLayerEntry', 'VisualSampleGroupEntry'),
        'tsas': ('TemporalSubLayerEntry', 'VisualSampleGroupEntry'),
        'stsa': ('StepwiseTemporalLayerEntry', 'VisualSampleGroupEntry'),
        'sdep': ('SampleDependencyBox', 'FullBox'),
        'seii': ('SeiInformationBox', 'Box'),
        'mvci': ('MultiviewInformationBox', 'FullBox'),
        'mvra': ('MultiviewRelationAttributeBox', 'FullBox'),
    }),
    ({
        'name': 'ISO/IEC 23008-12',
        'title': 'Information technology — MPEG systems technologies — Part 12: Image File Format',
        'version': '17 January 2014 working draft',
        'url': 'https://www.iso.org/standard/83650.html',
    }, {
        'ccst': ('CodingConstraintsBox', 'FullBox'),
        'vsmi': ('VisualSampleToMetadataItemEntry', 'VisualSampleGroupEntry'),
        'mint': ('MetadataIntegrityBox', 'FullBox'),
    }),
    ({
        'title': 'Encapsulation of Opus in ISO Base Media File Format',
        'version': '0.8.1 (incomplete)',
        'url': 'https://vfrmaniac.fushizen.eu/contents/opus_in_isobmff.html'
    }, {
        'Opus': ('OpusSampleEntry', 'AudioSampleEntry'),
        'dOps': ('OpusSpecificBox', 'Box'),
    }),
    ({
        'title': 'AV1 Codec ISO Media File Format Binding',
        'version': 'v1.2.0',
        'url': 'https://aomediacodec.github.io/av1-isobmff/v1.2.0.html',
    }, {
        'av01': ('AV1SampleEntry', 'VisualSampleEntry'),
        'av1C': ('AV1CodecConfigurationBox', 'Box'),
        'av1f': ('AV1ForwardKeyFrameSampleGroupEntry', 'VisualSampleGroupEntry'),
        'av1m': ('AV1MultiFrameSampleGroupEntry', 'VisualSampleGroupEntry'),
        'av1s': ('AV1SwitchFrameSampleGroupEntry', 'VisualSampleGroupEntry'),
        'av1M': ('AV1MetadataSampleGroupEntry', 'VisualSampleGroupEntry'),
    }),
    ({
        'title': '[ad-hoc]',
        'url': 'https://mp4ra.org/#/references',
    }, {
        'ID32': ('ID3v2Box', 'FullBox'),
    }),
]

info_by_box = {}
for std_desc, boxes in box_registry:
    for k, v in boxes.items():
        if k in info_by_box:
            raise Exception(f'duplicate boxes {k} coming from {std_desc} and {info_by_box[k][0]}')
        info_by_box[k] = (std_desc, *v)

def slice_box(mem: memoryview):
    #assert len(mem) >= 8, f'box too short ({bytes(mem)})'
    length, btype = struct.unpack('>I4s', mem[0:8])
    btype = btype.decode('latin1')
    #assert btype.isprintable(), f'invalid type {repr(btype)}'

    last_box = False
    large_size = False
    pos = 8
    if length == 0:
        length = len(mem)
        last_box = True
    elif length == 1:
        large_size = True
        #assert len(mem) >= pos + 8, f'EOF while reading largesize'
        length, = struct.unpack('>Q', mem[pos:pos + 8])
        pos += 8

    if btype == 'uuid':
        #assert len(mem) >= pos + 16, f'EOF while reading UUID'
        btype = mem[pos:pos + 16].hex()
        pos += 16

    #assert length >= pos, f'invalid {btype} length: {length}'
    #assert len(mem) >= length, f'expected {length} {btype}, got {len(mem)}'
    return (btype, mem[pos:length], last_box, large_size), length

def parse_boxes(offset: int, mem: memoryview, indent=0, contents_fn=None):
    prefix = ' ' * (indent * indent_n)
    result = []
    while not MONITOR.abortRequested() and mem:
        (btype, data, last_box, large_size), length = slice_box(mem)
        offset_text = ansi_fg4(f' @ {offset:#x}, {offset + length - len(data):#x} - {offset + length:#x}') if show_offsets else ''
        length_text = ansi_fg4(f' ({len(data)})') if show_lengths else ''
        name_text = ''
        if show_descriptions and (box_desc := info_by_box.get(btype)):
            desc = box_desc[1]
            if desc.endswith('Box'): desc = desc[:-3]
            name_text = ansi_bold(f' {desc}')
        if last_box:
            offset_text = ' (last)' + offset_text
        if large_size:
            offset_text = ' (large size)' + offset_text
        type_label = btype
        if len(btype) != 4: # it's a UUID
            type_label = '-'.join(btype[s:e] for s, e in pairwise([0, 8, 12, 16, 20, 32]) )
            type_label = f'UUID {type_label}'
        metaPrint(prefix + ansi_bold(f'[{type_label}]') + name_text + offset_text + length_text)
        result.append( (contents_fn or parse_contents)(btype, offset + length - len(data), data, indent + 1) )
        mem, offset = mem[length:], offset + length
    return result

nesting_boxes = { 'moov', 'trak', 'mdia', 'minf', 'dinf', 'stbl', 'mvex', 'moof', 'traf', 'mfra', 'meco', 'edts', 'udta' }
nesting_boxes |= { 'ilst', '\u00a9too', '\u00a9nam', '\u00a9day', '\u00a9ART', 'aART', '\u00a9alb', '\u00a9cmt', '\u00a9day', 'trkn', 'covr', '----' }

def parse_contents(btype: str, offset: int, data: memoryview, indent):
    prefix = ' ' * (indent * indent_n)
    try:

        if (handler := globals().get(f'parse_{btype}_box')):
            return handler(offset, data, indent)

        if btype in nesting_boxes:
            return parse_boxes(offset, data, indent)

    except Exception as e:
        print_error(e, prefix)

    # as fall back (or if error), print hex dump
    if not max_dump or not data: return
    print_hex_dump(data, prefix)

def parse_fullbox(data: io.BytesIO, prefix: str):
    fv = data.read(4)
    #assert len(fv) == 4
    return fv[0], int.from_bytes(fv[1:], 'big')

def parse_skip_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    if any(bytes(data)):
        print_hex_dump(data, prefix)
    else:
        metaPrint(prefix + ansi_dim(ansi_fg2(f'({len(data)} empty bytes)')))

parse_free_box = parse_skip_box


# BOX CONTAINERS THAT ALSO HAVE A PREPENDED BINARY STRUCTURE

def parse_meta_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    metaPrint(prefix + f'version = {version}, flags = {box_flags:06x}')
    parse_boxes(offset + data.tell(), memoryview(data.read()), indent)

# hack: use a global variable because I'm too lazy to rewrite everything to pass this around
# FIXME: remove this hack, which is sometimes unreliable since there can be inner handlers we don't care about
last_handler_seen = None

def parse_hdlr_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0 and box_flags == 0, 'invalid version / flags'
    pre_defined, handler_type = unpack(data, 'I4s')
    handler_type = handler_type.decode('latin1')
    reserved = data.read(4 * 3)
    # FIXME: a lot of videos seem to break the second assertion (apple metadata?), some break the first
    #assert not pre_defined, f'invalid pre-defined: {pre_defined}'
    #assert not any(reserved), f'invalid reserved: {reserved}'
    name = data.read().decode('utf-8')
    metaPrint(prefix + f'handler_type = {repr(handler_type)}, name = {repr(name)}')

    global last_handler_seen
    last_handler_seen = handler_type

def parse_stsd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'version = {version}, entry_count = {entry_count}')
    #assert box_flags == 0, f'invalid flags: {box_flags:06x}'

    contents_fn = lambda *a, **b: parse_sample_entry_contents(*a, **b, version=version)
    boxes = parse_boxes(offset + data.tell(), memoryview(data.read()), indent, contents_fn=contents_fn)
    #assert len(boxes) == entry_count, f'entry_count not matching boxes present'

def parse_sample_entry_contents(btype: str, offset: int, data: memoryview, indent: int, version: int):
    prefix = ' ' * (indent * indent_n)

    #assert len(data) >= 6 + 2, 'entry too short'
    #assert data[:6] == b'\x00\x00\x00\x00\x00\x00', f'invalid reserved field: {data[:6]}'
    data_reference_index, = struct.unpack('>H', data[6:8])
    data = data[8:]; offset += 8
    metaPrint(prefix + f'data_reference_index = {data_reference_index}')

    try:
        if last_handler_seen == 'vide':
            return parse_video_sample_entry_contents(btype, offset, data, indent, version)
        if last_handler_seen == 'soun':
            return parse_audio_sample_entry_contents(btype, offset, data, indent, version)
        if last_handler_seen in {'meta', 'text', 'subt'}:
            return parse_text_sample_entry_contents(btype, offset, data, indent, version)
    except Exception as e:
        print_error(e, prefix)

    # as fall back (or if error), print hex dump
    if not max_dump or not data: return
    print_hex_dump(data, prefix)

def parse_video_sample_entry_contents(btype: str, offset: int, data: memoryview, indent: int, version: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    #assert version == 0, 'invalid version'

    reserved = data.read(16)
    #assert not any(reserved), f'invalid reserved / pre-defined data: {reserved}'
    width, height, horizresolution, vertresolution, reserved_2, frame_count, compressorname, depth, pre_defined_3 = unpack(data, 'HHIIIH 32s Hh')
    metaPrint(prefix + f'size = {width} x {height}')
    if show_defaults or horizresolution != 0x00480000 or vertresolution != 0x00480000:
        metaPrint(prefix + f'resolution = {horizresolution} x {vertresolution}')
    if show_defaults or frame_count != 1:
        metaPrint(prefix + f'frame count = {frame_count}')

    compressorname_len, compressorname = compressorname[0], compressorname[1:]
    #assert compressorname_len <= len(compressorname)
    #assert not any(compressorname[compressorname_len:]), 'invalid compressorname padding'
    compressorname = compressorname[:compressorname_len].decode('utf-8')
    metaPrint(prefix + f'compressorname = {repr(compressorname)}')

    if show_defaults or depth != 0x0018:
        metaPrint(prefix + f'depth = {depth}')
    #assert not reserved_2, f'invalid reserved: {reserved_2}'
    #assert pre_defined_3 == -1, f'invalid reserved: {pre_defined_3}'

    parse_boxes(offset + data.tell(), memoryview(data.read()), indent)

def parse_audio_sample_entry_contents(btype: str, offset: int, data: memoryview, indent: int, version: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    #assert version <= 1, 'invalid version'

    if version == 0:
        reserved_1, channelcount, samplesize, pre_defined_1, reserved_2, samplerate = unpack(data, '8sHHHHI')
        #assert not any(reserved_1), f'invalid reserved_1: {reserved_1}'
        #assert not reserved_2, f'invalid reserved_2: {reserved_2}'
        #assert not pre_defined_1, f'invalid pre_defined_1: {pre_defined_1}'
        if show_defaults or channelcount != 2:
            metaPrint(prefix + f'channelcount = {channelcount}')
        if show_defaults or samplesize != 16:
            metaPrint(prefix + f'samplesize = {samplesize}')
        metaPrint(prefix + f'samplerate = {samplerate / (1 << 16)}')
    else:
        entry_version, reserved_1, channelcount, samplesize, pre_defined_1, reserved_2, samplerate = unpack(data, 'H6sHHHHI')
        #assert entry_version == 1, f'invalid entry_version: {entry_version}'
        #assert not any(reserved_1), f'invalid reserved_1: {reserved_1}'
        #assert not reserved_2, f'invalid reserved_2: {reserved_2}'
        #assert not pre_defined_1, f'invalid pre_defined_1: {pre_defined_1}'
        metaPrint(prefix + f'channelcount = {channelcount}')
        if show_defaults or samplesize != 16:
            metaPrint(prefix + f'samplesize = {samplesize}')
        if show_defaults or samplerate != (1 << 16):
            metaPrint(prefix + f'samplerate = {samplerate / (1 << 16)}')

    parse_boxes(offset + data.tell(), memoryview(data.read()), indent)

def parse_text_sample_entry_contents(btype: str, offset: int, data: memoryview, indent: int, version: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    #assert version == 0, 'invalid version'

    fields = {
        # meta
        'metx': ('content_encoding', 'namespace', 'schema_location'),
        'mett': ('content_encoding', 'mime_format'),
        'urim': (),
        # text
        'stxt': ('content_encoding', 'mime_format'),
        # subt
        'sbtt': ('content_encoding', 'mime_format'),
        'stpp': ('namespace', 'schema_location', 'auxiliary_mime_types'),
    }.get(btype, [])
    for field_name in fields:
        metaPrint(prefix + f'{field_name} = {repr(read_string(data))}')

    parse_boxes(offset + data.tell(), memoryview(data.read()), indent)

# HEADER BOXES
def parse_ftyp_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    major_brand, minor_version = unpack(data, '4sI')
    major_brand = major_brand.decode('latin1')
    metaPrint(prefix + f'major_brand = {repr(major_brand)}')
    metaPrint(prefix + f'minor_version = {minor_version:08x}')
    while not MONITOR.abortRequested() and (compatible_brand := data.read(4)):
        #assert len(compatible_brand), 'invalid brand length'
        metaPrint(prefix + f'- compatible: {repr(compatible_brand.decode("latin1"))}')

parse_styp_box = parse_ftyp_box

def parse_matrix(data: io.BytesIO, prefix: str):
    matrix = [ x / (1 << 16) for x in unpack(data, '9i') ]
    if show_defaults or matrix != [1,0,0, 0,1,0, 0,0,0x4000]:
        metaPrint(prefix + f'matrix = {matrix}')

def parse_language(data: io.BytesIO, prefix: str):
    language, = unpack(data, 'H')
    if not language:
        metaPrint(prefix + 'language = (null)') # FIXME: log a warning or something
        return
    pad, *language = split_bits(language, 16, 15, 10, 5, 0)
    #assert all(0 <= (x - 1) < 26 for x in language), f'invalid language characters: {language}'
    language = ''.join(chr((x - 1) + ord('a')) for x in language)
    metaPrint(prefix + f'language = {language}')
    #assert not pad, f'invalid pad: {pad}'

def parse_mfhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 0, f'invalid flags: {box_flags}'

    sequence_number, = unpack(data, 'I')
    metaPrint(prefix + f'sequence_number = {sequence_number}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_mvhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version <= 1, f'invalid version: {version}'
    #assert not box_flags, f'invalid flags: {box_flags}'
    metaPrint(prefix + f'version = {version}')

    creation_time, modification_time, timescale, duration, rate, volume, reserved_1, reserved_2, reserved_3 = \
        unpack(data, ('QQIQ' if version == 1 else 'IIII') + 'ih' + 'HII')
    metaPrint(prefix + f'creation_time = {creation_time}')
    metaPrint(prefix + f'modification_time = {modification_time}')
    metaPrint(prefix + f'timescale = {timescale}')
    duration = (duration // timescale)
    metaPrint(prefix + f'duration = {duration}')
    durations.append(duration)
    rate /= 1 << 16
    if show_defaults or rate != 1: metaPrint(prefix + f'rate = {rate}')
    volume /= 1 << 8
    if show_defaults or volume != 1: metaPrint(prefix + f'volume = {volume}')
    #assert not reserved_1, f'invalid reserved_1: {reserved_1}'
    #assert not reserved_2, f'invalid reserved_1: {reserved_2}'
    #assert not reserved_3, f'invalid reserved_1: {reserved_3}'

    parse_matrix(data, prefix)
    pre_defined = data.read(6 * 4)
    #assert not any(pre_defined), f'invalid pre_defined: {pre_defined}'
    next_track_ID, = unpack(data, 'I')
    metaPrint(prefix + f'next_track_ID = {next_track_ID}')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_tkhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version <= 1, f'invalid version: {version}'
    metaPrint(prefix + f'version = {version}, flags = {box_flags:06x}')

    creation_time, modification_time, track_ID, reserved_1, duration, reserved_2, reserved_3, layer, alternate_group, volume, reserved_4 = \
        unpack(data, ('QQIIQ' if version == 1 else 'IIIII') + 'II' + 'hhh' + 'H')
    metaPrint(prefix + f'creation_time = {creation_time}')
    metaPrint(prefix + f'modification_time = {modification_time}')
    metaPrint(prefix + f'track_ID = {track_ID}')
    duration = duration // 1000
    metaPrint(prefix + f'duration = {duration}')
    durations.append(duration)
    if show_defaults or layer != 0:
        metaPrint(prefix + f'layer = {layer}')
    if show_defaults or alternate_group != 0:
        metaPrint(prefix + f'alternate_group = {alternate_group}')
    volume /= 1 << 8
    metaPrint(prefix + f'volume = {volume}')
    #assert not reserved_1, f'invalid reserved_1: {reserved_1}'
    #assert not reserved_2, f'invalid reserved_1: {reserved_2}'
    #assert not reserved_3, f'invalid reserved_1: {reserved_3}'
    #assert not reserved_4, f'invalid reserved_1: {reserved_4}'

    parse_matrix(data, prefix)
    width, height = unpack(data, 'II')
    width /= 1 << 16
    height /= 1 << 16
    metaPrint(prefix + f'size = {width} x {height}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_mdhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version <= 1, f'invalid version: {version}'
    #assert not box_flags, f'invalid flags: {box_flags}'
    metaPrint(prefix + f'version = {version}')

    creation_time, modification_time, timescale, duration = \
        unpack(data, 'QQIQ' if version == 1 else 'IIII')
    metaPrint(prefix + f'creation_time = {creation_time}')
    metaPrint(prefix + f'modification_time = {modification_time}')
    metaPrint(prefix + f'timescale = {timescale}')
    duration = duration // timescale
    metaPrint(prefix + f'duration = {duration}')
    durations.append(duration)
    parse_language(data, prefix)
    pre_defined_1, = unpack(data, 'H')
    #assert not pre_defined_1, f'invalid reserved_1: {pre_defined_1}'

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_mehd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version <= 1, f'invalid version: {version}'
    #assert not box_flags, f'invalid flags: {box_flags}'
    metaPrint(prefix + f'version = {version}')

    fragment_duration, = unpack(data, ('Q' if version == 1 else 'I'))
    fragment_duration = fragment_duration // 1000
    metaPrint(prefix + f'fragment_duration = {fragment_duration}')
    durations.append(fragment_duration)

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_smhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 0, f'invalid flags: {box_flags}'

    balance, reserved = unpack(data, 'hH')
    if show_defaults or balance != 0:
        metaPrint(prefix + f'balance = {balance}')
    #assert not reserved, f'invalid reserved: {reserved}'

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_vmhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 1, f'invalid flags: {box_flags}'

    graphicsmode, *opcolor = unpack(data, 'HHHH')
    if show_defaults or graphicsmode != 0:
        metaPrint(prefix + f'graphicsmode = {graphicsmode}')
    if show_defaults or opcolor != [0, 0, 0]:
        metaPrint(prefix + f'opcolor = {opcolor}')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_trex_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 0, f'invalid flags: {box_flags}'

    track_ID, default_sample_description_index, default_sample_duration, default_sample_size, default_sample_flags = \
        unpack(data, 'IIIII')
    metaPrint(prefix + f'track_ID = {track_ID}')
    metaPrint(prefix + f'default_sample_description_index = {default_sample_description_index}')
    metaPrint(prefix + f'default_sample_duration = {default_sample_duration}')
    metaPrint(prefix + f'default_sample_size = {default_sample_size}')
    metaPrint(prefix + f'default_sample_flags = {default_sample_flags:08x}')
    durations.append(default_sample_duration)

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

# NON CODEC-SPECIFIC BOXES
def parse_ID32_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    metaPrint(prefix + f'flags = {box_flags:06x}')
    parse_language(data, prefix)
    metaPrint(prefix + f'ID3v2 data =')
    print_hex_dump(data.read(), prefix + '  ')

def parse_dref_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    entry_count, = unpack(data, 'I')
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 0, f'invalid flags: {box_flags:06x}'
    metaPrint(prefix + f'version = {version}, entry_count = {entry_count}')

    boxes = parse_boxes(offset + data.tell(), memoryview(data.read()), indent)
    #assert len(boxes) == entry_count, f'entry_count not matching boxes present'

def parse_url_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    metaPrint(prefix + f'flags = {box_flags:06x}')
    if (location := read_string(data, optional=True)) != None:
        metaPrint(prefix + f'location = {repr(location)}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_urn_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    metaPrint(prefix + f'flags = {box_flags:06x}')
    if (location := read_string(data, optional=True)) != None:
        metaPrint(prefix + f'location = {repr(location)}')
    if (name := read_string(data, optional=True)) != None:
        metaPrint(prefix + f'name = {repr(name)}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

globals()['parse_url _box'] = parse_url_box
globals()['parse_urn _box'] = parse_urn_box

def parse_colr_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    colour_type, = unpack(data, '4s')
    colour_type = colour_type.decode('latin1')
    descriptions = {
        'nclx': 'on-screen colours',
        'rICC': 'restricted ICC profile',
        'prof': 'unrestricted ICC profile',
    }
    description = f' ({descriptions[colour_type]})' if show_descriptions and colour_type in descriptions else ''
    metaPrint(prefix + f'colour_type = {repr(colour_type)}' + description)
    if colour_type == 'nclx':
        colour_primaries, transfer_characteristics, matrix_coefficients, flags = unpack(data, 'HHHB')
        metaPrint(prefix + f'colour_primaries = {colour_primaries}')
        metaPrint(prefix + f'transfer_characteristics = {transfer_characteristics}')
        metaPrint(prefix + f'matrix_coefficients = {matrix_coefficients}')
        full_range_flag, reserved = split_bits(flags, 8, 7, 0)
        #assert not reserved, f'invalid reserved: {reserved}'
        metaPrint(prefix + f'full_range_flag = {bool(full_range_flag)}')
    else:
        name = 'ICC_profile' if colour_type in { 'rICC', 'prof' } else 'data'
        metaPrint(prefix + f'{name} =')
        print_hex_dump(data.read(), prefix + '  ')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_btrt_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    bufferSizeDB, maxBitrate, avgBitrate = unpack(data, 'III')
    metaPrint(prefix + f'bufferSizeDB = {bufferSizeDB}')
    metaPrint(prefix + f'maxBitrate = {maxBitrate}')
    metaPrint(prefix + f'avgBitrate = {avgBitrate}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_pasp_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    hSpacing, vSpacing = unpack(data, 'II')
    metaPrint(prefix + f'pixel aspect ratio = {hSpacing}/{vSpacing}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_clap_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    cleanApertureWidthN, cleanApertureWidthD, cleanApertureHeightN, cleanApertureHeightD, horizOffN, horizOffD, vertOffN, vertOffD = unpack(data, 'II II II II')
    metaPrint(prefix + f'cleanApertureWidth = {cleanApertureWidthN}/{cleanApertureWidthD}')
    metaPrint(prefix + f'cleanApertureHeight = {cleanApertureHeightN}/{cleanApertureHeightD}')
    metaPrint(prefix + f'horizOff = {horizOffN}/{horizOffD}')
    metaPrint(prefix + f'vertOff = {vertOffN}/{vertOffD}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

# CODEC-SPECIFIC BOXES
def parse_avcC_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    configurationVersion, = data.read(1)
    #assert configurationVersion == 1, f'invalid configuration version: {configurationVersion}'
    avcProfileCompFlags = data.read(3)
    metaPrint(prefix + f'profile / compat / level = {avcProfileCompFlags.hex()}')
    composite_1, composite_2 = data.read(2)
    reserved_1, lengthSizeMinusOne = split_bits(composite_1, 8, 2, 0)
    reserved_2, numOfSequenceParameterSets = split_bits(composite_2, 8, 5, 0)
    #assert reserved_1 == mask(6), f'invalid reserved_1: {reserved_1}'
    #assert reserved_2 == mask(3), f'invalid reserved_2: {reserved_2}'
    metaPrint(prefix + f'lengthSizeMinusOne = {lengthSizeMinusOne}')

    for i in range(numOfSequenceParameterSets):
        size, = unpack(data, 'H')
        sps = data.read(size)
        #assert len(sps) == size, f'not enough SPS data: expected {size}, found {len(sps)}'
        metaPrint(prefix + f'- SPS: {sps.hex()}')
    numOfPictureParameterSets, = data.read(1)
    for i in range(numOfPictureParameterSets):
        size, = unpack(data, 'H')
        pps = data.read(size)
        #assert len(pps) == size, f'not enough PPS data: expected {size}, found {len(pps)}'
        metaPrint(prefix + f'- PPS: {pps.hex()}')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_svcC_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    configurationVersion, = data.read(1)
    #assert configurationVersion == 1, f'invalid configuration version: {configurationVersion}'
    avcProfileCompFlags = data.read(3)
    metaPrint(prefix + f'profile / compat / level = {avcProfileCompFlags.hex()}')
    composite_1, composite_2 = data.read(2)
    complete_represenation, reserved_1, lengthSizeMinusOne = split_bits(composite_1, 8, 7, 2, 0)
    reserved_2, numOfSequenceParameterSets = split_bits(composite_2, 8, 7, 0)
    #assert reserved_1 == mask(5), f'invalid reserved_1: {reserved_1}'
    #assert reserved_2 == 0, f'invalid reserved_2: {reserved_2}'
    metaPrint(prefix + f'complete_represenation = {bool(complete_represenation)}')
    metaPrint(prefix + f'lengthSizeMinusOne = {lengthSizeMinusOne}')

    for i in range(numOfSequenceParameterSets):
        size, = unpack(data, 'H')
        sps = data.read(size)
        #assert len(sps) == size, f'not enough SPS data: expected {size}, found {len(sps)}'
        metaPrint(prefix + f'- SPS: {sps.hex()}')
    numOfPictureParameterSets, = data.read(1)
    for i in range(numOfPictureParameterSets):
        size, = unpack(data, 'H')
        pps = data.read(size)
        #assert len(sps) == size, f'not enough PPS data: expected {size}, found {len(pps)}'
        metaPrint(prefix + f'- PPS: {pps.hex()}')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_hvcC_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    configurationVersion, = data.read(1)
    #assert configurationVersion == 1, f'invalid configuration version: {configurationVersion}'

    composite_1, general_profile_compatibility_flags, general_constraint_indicator_flags, general_level_idc, min_spatial_segmentation_idc, \
    parallelismType, chromaFormat, bitDepthLumaMinus8, bitDepthChromaMinus8, \
    avgFrameRate, composite_2 = \
        unpack(data, 'B I 6s B H  B B B B  H B')
    general_constraint_indicator_flags = int.from_bytes(general_constraint_indicator_flags, 'big')
    general_profile_space, general_tier_flag, general_profile_idc = split_bits(composite_1, 8, 6, 5, 0)
    constantFrameRate, numTemporalLayers, temporalIdNested, lengthSizeMinusOne = split_bits(composite_2, 8, 6, 3, 2, 0)

    metaPrint(prefix + f'general_profile_space = {general_profile_space}')
    metaPrint(prefix + f'general_tier_flag = {general_tier_flag}')
    metaPrint(prefix + f'general_profile_idc = {general_profile_idc:02x}')

    metaPrint(prefix + f'general_profile_compatibility_flags = {general_profile_compatibility_flags:08x}')
    metaPrint(prefix + f'general_constraint_indicator_flags = {general_constraint_indicator_flags:012x}')
    metaPrint(prefix + f'general_level_idc = {general_level_idc:02x}')

    reserved, min_spatial_segmentation_idc = split_bits(min_spatial_segmentation_idc, 16, 12, 0)
    #assert reserved == mask(4), f'invalid reserved: {reserved}'
    metaPrint(prefix + f'min_spatial_segmentation_idc = {min_spatial_segmentation_idc}')
    reserved, parallelismType = split_bits(parallelismType, 8, 2, 0)
    #assert reserved == mask(6), f'invalid reserved: {reserved}'
    metaPrint(prefix + f'parallelismType = {parallelismType}')
    reserved, chromaFormat = split_bits(chromaFormat, 8, 2, 0)
    #assert reserved == mask(6), f'invalid reserved: {reserved}'
    metaPrint(prefix + f'chromaFormat = {chromaFormat}')
    reserved, bitDepthLumaMinus8 = split_bits(bitDepthLumaMinus8, 8, 3, 0)
    #assert reserved == mask(5), f'invalid reserved: {reserved}'
    metaPrint(prefix + f'bitDepthLumaMinus8 = {bitDepthLumaMinus8}')
    reserved, bitDepthChromaMinus8 = split_bits(bitDepthChromaMinus8, 8, 3, 0)
    #assert reserved == mask(5), f'invalid reserved: {reserved}'
    metaPrint(prefix + f'bitDepthChromaMinus8 = {bitDepthChromaMinus8}')

    metaPrint(prefix + f'avgFrameRate = {avgFrameRate}')
    metaPrint(prefix + f'constantFrameRate = {constantFrameRate}')
    metaPrint(prefix + f'numTemporalLayers = {numTemporalLayers}')
    metaPrint(prefix + f'temporalIdNested = {bool(temporalIdNested)}')
    metaPrint(prefix + f'lengthSizeMinusOne = {lengthSizeMinusOne}')

    numOfArrays, = unpack(data, 'B')
    #metaPrint(prefix + f'numOfArrays = {numOfArrays}')
    for i in range(numOfArrays):
        metaPrint(prefix + f'- array {i}:')
        composite, numNalus = unpack(data, 'BH')
        array_completeness, reserved, NAL_unit_type = split_bits(composite, 8, 7, 6, 0)
        #assert reserved == 0, f'invalid reserved: {reserved}'

        metaPrint(prefix + f'    array_completeness = {bool(array_completeness)}')
        metaPrint(prefix + f'    NAL_unit_type = {NAL_unit_type}')
        #metaPrint(prefix + f'    numNalus = {numNalus}')

        for n in range(numNalus):
            entry_start = offset + data.tell()
            nalUnitLength, = unpack(data, 'H')
            data_start = offset + data.tell()
            nalData = data.read(nalUnitLength)
            #assert len(nalData) == nalUnitLength, f'EOF when reading NALU: expected {nalUnitLength}, got {len(nalData)}'

            offset_text = ansi_fg4(f' @ {entry_start:#x}, {data_start:#x} - {data_start + nalUnitLength:#x}') if show_offsets else ''
            length_text = ansi_fg4(f' ({nalUnitLength})') if show_lengths else ''
            metaPrint(prefix + f'    - NALU {n}' + offset_text + length_text)
            print_hex_dump(nalData, prefix + '        ')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_esds_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'
    #assert box_flags == 0, f'invalid flags: {box_flags:06x}'
    parse_descriptor(data, indent, expected=3)
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

parse_iods_box = parse_esds_box

def parse_m4ds_box(offset: int, data: memoryview, indent: int):
    data = io.BytesIO(data)
    parse_descriptors(data, indent)
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_dOps_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)

    Version, OutputChannelCount, PreSkip, InputSampleRate, OutputGain, ChannelMappingFamily = unpack(data, 'BBHIhB')
    #assert Version == 0, f'invalid Version: {Version}'
    OutputGain /= 1 << 8
    metaPrint(prefix + f'OutputChannelCount = {OutputChannelCount}')
    metaPrint(prefix + f'PreSkip = {PreSkip}')
    metaPrint(prefix + f'InputSampleRate = {InputSampleRate}')
    metaPrint(prefix + f'OutputGain = {OutputGain}')
    metaPrint(prefix + f'ChannelMappingFamily = {ChannelMappingFamily}')
    if ChannelMappingFamily != 0:
        StreamCount, CoupledCount = data.read(2)
        metaPrint(prefix + f'StreamCount = {StreamCount}')
        metaPrint(prefix + f'CoupledCount = {CoupledCount}')
        ChannelMapping = data.read(OutputChannelCount)
        #assert len(ChannelMapping) == OutputChannelCount, 'invalid ChannelMapping length'
        metaPrint(prefix + f'ChannelMapping = {ChannelMapping}')
    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

# TABLES
def parse_elst_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version <= 1, f'invalid version: {version}'
    metaPrint(prefix + f'version = {version}')

    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        segment_duration, media_time, media_rate = \
            unpack(data, ('Qq' if version == 1 else 'Ii') + 'i')
        media_rate /= 1 << 16
        if i < max_rows:
            segment_duration = segment_duration // 1000
            metaPrint(prefix + f'[edit segment {i:3}] duration = {segment_duration:6}, media_time = {media_time:6}, media_rate = {media_rate}')
            durations.append(segment_duration)
    if entry_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_sidx_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version <= 1, f'invalid version: {version}'
    metaPrint(prefix + f'version = {version}')

    reference_ID, timescale, earliest_presentation_time, first_offset, reserved_1, reference_count = \
        unpack(data, 'II' + ('II' if version == 0 else 'QQ') + 'HH')
    metaPrint(prefix + f'reference_ID = {reference_ID}')
    metaPrint(prefix + f'timescale = {timescale}')
    metaPrint(prefix + f'earliest_presentation_time = {earliest_presentation_time}')
    metaPrint(prefix + f'first_offset = {first_offset}')
    metaPrint(prefix + f'reference_count = {reference_count}')
    #assert not reserved_1, f'invalid reserved_1 = {reserved_1}'
    for i in range(reference_count):
        composite_1, subsegment_duration, composite_2 = unpack(data, 'III')
        reference_type, referenced_size = split_bits(composite_1, 32, 31, 0)
        starts_with_SAP, SAP_type, SAP_delta_time = split_bits(composite_2, 32, 31, 28, 0)
        if i < max_rows:
            metaPrint(prefix + f'[reference {i:3}] type = {reference_type}, size = {referenced_size}, duration = {subsegment_duration}, starts_with_SAP = {starts_with_SAP}, SAP_type = {SAP_type}, SAP_delta_time = {SAP_delta_time}')
            durations.append(subsegment_duration)
    if reference_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_stts_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    sample, time = 1, 0
    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        sample_count, sample_delta = unpack(data, 'II')
        if i < max_rows:
            metaPrint(prefix + f'[entry {i:3}] [sample = {sample:6}, time = {time:6}] sample_count = {sample_count:5}, sample_delta = {sample_delta:5}')
        sample += sample_count
        time += sample_count * sample_delta
    if entry_count > max_rows:
        metaPrint(prefix + '...')
    metaPrint(prefix + f'[samples = {sample-1:6}, time = {time:6}]')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_ctts_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version <= 1, f'invalid version: {version}'
    metaPrint(prefix + f'version = {version}')

    sample = 1
    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        sample_count, sample_offset = unpack(data, 'I' + ('i' if version==1 else 'I'))
        if i < max_rows:
            metaPrint(prefix + f'[entry {i:3}] [sample = {sample:6}] sample_count = {sample_count:5}, sample_offset = {sample_offset:5}')
        sample += sample_count
    if entry_count > max_rows:
        metaPrint(prefix + '...')
    metaPrint(prefix + f'[samples = {sample-1:6}]')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_stsc_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    sample, last_chunk, last_spc = 1, None, None
    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        first_chunk, samples_per_chunk, sample_description_index = unpack(data, 'III')
        if last_chunk != None:
            #assert first_chunk > last_chunk
            sample += last_spc * (first_chunk - last_chunk)
        if i < max_rows:
            metaPrint(prefix + f'[entry {i:3}] [sample = {sample:6}] first_chunk = {first_chunk:5}, samples_per_chunk = {samples_per_chunk:4}, sample_description_index = {sample_description_index}')
        last_chunk, last_spc = first_chunk, samples_per_chunk
    if entry_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_stsz_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    sample_size, sample_count = unpack(data, 'II')
    if show_defaults or sample_size != 0:
        metaPrint(prefix + f'sample_size = {sample_size}')
    metaPrint(prefix + f'sample_count = {sample_count}')
    if sample_size == 0:
        for i in range(sample_count):
            sample_size, = unpack(data, 'I')
            if i < max_rows:
                metaPrint(prefix + f'[sample {i+1:6}] sample_size = {sample_size:5}')
        if sample_count > max_rows:
            metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_stco_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        chunk_offset, = unpack(data, 'I')
        if i < max_rows:
            metaPrint(prefix + f'[chunk {i+1:5}] offset = {chunk_offset:#08x}')
    if entry_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_co64_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        chunk_offset, = unpack(data, 'Q')
        if i < max_rows:
            metaPrint(prefix + f'[chunk {i+1:5}] offset = {chunk_offset:#016x}')
    if entry_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_stss_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version == 0, f'invalid version: {version}'

    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        sample_number, = unpack(data, 'I')
        if i < max_rows:
            metaPrint(prefix + f'[sync sample {i:5}] sample_number = {sample_number:6}')
    if entry_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_sbgp_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert not box_flags, f'invalid box_flags: {box_flags}'
    #assert version <= 1, f'invalid version: {version}'
    metaPrint(prefix + f'version = {version}')

    grouping_type, = unpack(data, '4s')
    grouping_type = grouping_type.decode('latin1')
    metaPrint(prefix + f'grouping_type = {repr(grouping_type)}')
    if version == 1:
        grouping_type_parameter, = unpack(data, 'I')
        metaPrint(prefix + f'grouping_type_parameter = {grouping_type_parameter}')

    sample = 1
    entry_count, = unpack(data, 'I')
    metaPrint(prefix + f'entry_count = {entry_count}')
    for i in range(entry_count):
        sample_count, group_description_index = unpack(data, 'II')
        if i < max_rows:
            metaPrint(prefix + f'[entry {i+1:5}] [sample = {sample:6}] sample_count = {sample_count:5}, group_description_index = {group_description_index:5}')
        sample += sample_count
    if entry_count > max_rows:
        metaPrint(prefix + '...')
    metaPrint(prefix + f'[samples = {sample-1:6}]')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_tfdt_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version <= 1, f'invalid version: {version}'

    base_media_decode_time, = unpack(data, 'I' if version == 0 else 'Q')
    metaPrint(prefix + f'version = {version}, flags = {box_flags:06x}')
    metaPrint(prefix + f'baseMediaDecodeTime = {base_media_decode_time}')

def parse_tfhd_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)
    #assert version == 0, f'invalid version: {version}'

    metaPrint(prefix + f'version = {version}, flags = {box_flags:06x}')
    track_ID, = unpack(data, 'I')
    metaPrint(prefix + f'track_ID = {track_ID}')
    if box_flags & 0x10000:  # duration‐is‐empty
        metaPrint(prefix + 'duration-is-empty flag set')
    if box_flags & 0x20000:  # default-base-is-moof
        metaPrint(prefix + 'default-base-is-moof flag set')

    if box_flags & 0x1:  # base‐data‐offset‐present
        base_data_offset, = unpack(data, 'Q')
        metaPrint(prefix + f'base_data_offset = {base_data_offset}')
    if box_flags & 0x2:  # sample-description-index-present
        sample_description_index, = unpack(data, 'I')
        metaPrint(prefix + f'sample_description_index = {sample_description_index}')
    if box_flags & 0x8:  # default‐sample‐duration‐present
        default_sample_duration, = unpack(data, 'I')
        metaPrint(prefix + f'default_sample_duration = {default_sample_duration}')
        durations.append(default_sample_duration)
    if box_flags & 0x10:  # default‐sample‐size‐present
        default_sample_size, = unpack(data, 'I')
        metaPrint(prefix + f'default_sample_size = {default_sample_size}')

def parse_trun_box(offset: int, data: memoryview, indent: int):
    prefix = ' ' * (indent * indent_n)
    data = io.BytesIO(data)
    version, box_flags = parse_fullbox(data, prefix)

    sample_count, = unpack(data, 'I')
    metaPrint(prefix + f'version = {version}, flags = {box_flags:06x}, sample_count = {sample_count}')
    if box_flags & (1 << 0):
        data_offset, = unpack(data, 'i')
        metaPrint(prefix + f'data_offset = {data_offset:#x}')
    if box_flags & (1 << 2):
        first_sample_flags, = unpack(data, 'I')
        metaPrint(prefix + f'first_sample_flags = {first_sample_flags:08x}')

    s_offset = 0
    s_time = 0
    for s_idx in range(sample_count):
        s_text = []
        if box_flags & (1 << 8):
            sample_duration, = unpack(data, 'I')
            s_text.append(f'time={s_time:7} + {sample_duration:5}')
            s_time += sample_duration
        if box_flags & (1 << 9):
            sample_size, = unpack(data, 'I')
            s_text.append(f'offset={s_offset:#9x} + {sample_size:5}')
            s_offset += sample_size
        if box_flags & (1 << 10):
            sample_flags, = unpack(data, 'I')
            s_text.append(f'flags={sample_flags:08x}')
        if box_flags & (1 << 11):
            sample_composition_time_offset, = unpack(data, 'I' if version == 0 else 'i')
            s_text.append(f'{sample_composition_time_offset}')
        if s_idx < max_rows:
            metaPrint(prefix + f'[sample {s_idx:4}] {", ".join(s_text)}')
    if sample_count > max_rows:
        metaPrint(prefix + '...')

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing data'

def parse_descriptor(data, indent: int, expected=None, namespace='default', contents_fn=None, optional=False):
    tag = data.read(1)
    if optional and not tag: return None
    tag, = tag
    #assert tag != 0x00 and tag != 0xFF, f'forbidden tag number: {tag}'

    size = 0
    n_size_bytes = 0
    while not MONITOR.abortRequested():
        b = data.read(1)
        #assert b, f'unexpected EOF when reading descriptor size'
        next_byte, size_byte = split_bits(b[0], 8, 7, 0)
        size = (size << 7) | size_byte
        n_size_bytes += 1
        if not next_byte: break

    payload = data.read(size)
    #assert len(payload) == size, f'unexpected EOF within descriptor data: expected {size}, got {len(payload)}'
    data = io.BytesIO(payload)

    prefix = ' ' * (indent * indent_n)
    size_text = ''
    if size.bit_length() <= (n_size_bytes - 1) * 7:
        size_text = ansi_fg4(f' ({n_size_bytes} length bytes)')

    def get_class_chain(k):
        r = [k]
        while not MONITOR.abortRequested() and k['base_class'] != None:
            k = class_registry[k['base_class']][1]
            r.append(k)
        return r
    nsdata = descriptor_namespaces[namespace]
    labels = []
    if tag in nsdata['tag_registry']:
        klasses = get_class_chain(nsdata['tag_registry'][tag])
    else:
        labels.append(ansi_fg4('reserved for ISO use' if tag < nsdata['user_private'] else 'user private'))
        if k := next((k for (s, e, k) in nsdata['ranges'] if s <= tag < e), None):
            klasses = get_class_chain(class_registry[k][1])
    labels += [ ansi_bold(k['name']) for k in klasses ]

    metaPrint(prefix + ansi_bold(f'[{tag}]') + (' ' + ' -> '.join(labels) if show_descriptions else '') + size_text)
    (contents_fn or parse_descriptor_contents)(tag, klasses, data, indent + 1)

    left = data.read()
    #assert not left, f'{len(left)} bytes of trailing descriptor data'
    return tag,

def parse_descriptors(data, indent: int, **kwargs):
    while not MONITOR.abortRequested() and parse_descriptor(data, indent, **kwargs, optional=True) != None:
        pass

def parse_descriptor_contents(tag: int, klasses, data, indent: int):
    prefix = ' ' * (indent * indent_n)
    try:
        for k in klasses[::-1]:
            if 'handler' not in k: break
            k['handler'](data, indent)
    except Exception as e:
        print_error(e, prefix)

    # FIXME: should we backtrack here a bit? or too much? when a non-indented hexdump is printed, make it clear what it represents
    # as fall back (or if error), print hex dump
    data = data.read()
    if not max_dump or not data: return
    print_hex_dump(data, prefix)

def parse_BaseDescriptor_descriptor(data, indent: int):
    pass

def parse_ObjectDescriptorBase_descriptor(data, indent: int):
    pass

def parse_ExtensionDescriptor_descriptor(data, indent: int):
    pass

def parse_OCI_Descriptor_descriptor(data, indent: int):
    pass

def parse_IP_IdentificationDataSet_descriptor(data, indent: int):
    pass

def parse_ES_Descriptor_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    ES_ID, composite_1 = unpack(data, 'HB')
    streamDependenceFlag, URL_Flag, OCRstreamFlag, streamPriority = split_bits(composite_1, 8, 7, 6, 5, 0)
    metaPrint(prefix + f'ES_ID = {ES_ID}')
    metaPrint(prefix + f'streamPriority = {streamPriority}')
    if streamDependenceFlag:
        dependsOn_ES_ID, = unpack(data, 'H')
        metaPrint(prefix + f'dependsOn_ES_ID = {dependsOn_ES_ID}')
    if URL_Flag:
        URLlength, = unpack(data, 'B')
        URLstring = data.read(URLlength)
        #assert len(URLstring) == URLlength, f'unexpected EOF while reading URL, expected {URLlength}, found {len(URLstring)}'
        URLstring = URLstring.decode('utf-8')
        metaPrint(prefix + f'URL = {repr(URLstring)}')
    if OCRstreamFlag:
        OCR_ES_ID, = unpack(data, 'H')
        metaPrint(prefix + f'OCR_ES_ID = {OCR_ES_ID}')
    parse_descriptors(data, indent)

def parse_DecoderConfigDescriptor_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    objectTypeIndication, composite, maxBitrate, avgBitrate = unpack(data, 'BIII')
    streamType, upStream, reserved, bufferSizeDB = split_bits(composite, 32, 26, 25, 24, 0)
    metaPrint(prefix + f'objectTypeIndication = {objectTypeIndication}' + (f' ({format_object_type(objectTypeIndication)})' if show_descriptions else ''))
    metaPrint(prefix + f'streamType = {streamType}' + (f' ({format_stream_type(streamType)})' if show_descriptions else ''))
    metaPrint(prefix + f'upStream = {bool(upStream)}')
    metaPrint(prefix + f'bufferSizeDB = {bufferSizeDB}')
    metaPrint(prefix + f'maxBitrate = {maxBitrate}')
    metaPrint(prefix + f'avgBitrate = {avgBitrate}')
    #assert reserved == 1, f'invalid reserved: {reserved}'
    parse_descriptors(data, indent)

def parse_SLConfigDescriptor_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    predefined, = unpack(data, 'B')
    predefined_description = {
        0x00: 'Custom',
        0x01: 'null SL packet header',
        0x02: 'Reserved for use in MP4 files',
    }.get(predefined, 'Reserved for ISO use')
    metaPrint(prefix + f'predefined = {predefined}' + (f' ({predefined_description})' if show_descriptions else ''))
    if predefined != 0: return

    flags, timeStampResolution, OCRResolution, timeStampLength, OCRLength, AU_Length, instantBitrateLength, composite = \
        unpack(data, 'BIIBBBBH')
    useAccessUnitStartFlag, useAccessUnitEndFlag, useRandomAccessPointFlag, hasRandomAccessUnitsOnlyFlag, usePaddingFlag, useTimeStampsFlag, useIdleFlag, durationFlag = \
        split_bits(flags, 8, 7, 6, 5, 4, 3, 2, 1, 0)
    metaPrint(prefix + f'useAccessUnitStartFlag = {bool(useAccessUnitStartFlag)}')
    metaPrint(prefix + f'useAccessUnitEndFlag = {bool(useAccessUnitEndFlag)}')
    metaPrint(prefix + f'useRandomAccessPointFlag = {bool(useRandomAccessPointFlag)}')
    metaPrint(prefix + f'hasRandomAccessUnitsOnlyFlag = {bool(hasRandomAccessUnitsOnlyFlag)}')
    metaPrint(prefix + f'usePaddingFlag = {bool(usePaddingFlag)}')
    metaPrint(prefix + f'useTimeStampsFlag = {bool(useTimeStampsFlag)}')
    metaPrint(prefix + f'useIdleFlag = {bool(useIdleFlag)}')
    metaPrint(prefix + f'durationFlag = {bool(durationFlag)}')
    metaPrint(prefix + f'timeStampResolution = {timeStampResolution}')
    metaPrint(prefix + f'OCRResolution = {OCRResolution}')
    metaPrint(prefix + f'timeStampLength = {timeStampLength}')
    #assert timeStampLength <= 64, f'invalid timeStampLength: {timeStampLength}'
    metaPrint(prefix + f'OCRLength = {OCRLength}')
    #assert OCRLength <= 64, f'invalid OCRLength: {OCRLength}'
    metaPrint(prefix + f'AU_Length = {AU_Length}')
    #assert AU_Length <= 32, f'invalid AU_Length: {AU_Length}'
    metaPrint(prefix + f'instantBitrateLength = {instantBitrateLength}')
    degradationPriorityLength, AU_seqNumLength, packetSeqNumLength, reserved = split_bits(composite, 16, 12, 7, 2, 0)
    metaPrint(prefix + f'degradationPriorityLength = {degradationPriorityLength}')
    metaPrint(prefix + f'AU_seqNumLength = {AU_seqNumLength}')
    #assert AU_seqNumLength <= 16, f'invalid AU_seqNumLength: {AU_seqNumLength}'
    metaPrint(prefix + f'packetSeqNumLength = {packetSeqNumLength}')
    #assert packetSeqNumLength <= 16, f'invalid packetSeqNumLength: {packetSeqNumLength}'
    #assert reserved == 0b11, f'invalid reserved: {reserved}'
    if durationFlag:
        timeScale, accessUnitDuration, compositionUnitDuration = unpack(data, 'IHH')
        metaPrint(prefix + f'timeScale = {timeScale}')
        metaPrint(prefix + f'accessUnitDuration = {accessUnitDuration}')
        metaPrint(prefix + f'compositionUnitDuration = {compositionUnitDuration}')
    #if not useTimeStampsFlag:
        #assert False, 'FIXME: not implemented yet'
        # bit(timeStampLength) startDecodingTimeStamp;
        # bit(timeStampLength) startCompositionTimeStamp;

def parse_ES_ID_Inc_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    Track_ID, = unpack(data, 'I')
    metaPrint(prefix + f'Track_ID = {Track_ID}')

def parse_ES_ID_Ref_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    ref_index, = unpack(data, 'H')
    metaPrint(prefix + f'ref_index = {ref_index}')

def parse_ExtendedSLConfigDescriptor_descriptor(data, indent: int):
    parse_descriptors(data, indent)

def parse_QoS_Descriptor_descriptor(data, indent: int):
    prefix = ' ' * (indent * indent_n)
    predefined, = unpack(data, 'B')
    predefined_description = {
        0x00: 'Custom',
    }.get(predefined, 'Reserved')
    metaPrint(prefix + f'predefined = {predefined}' + (f' ({predefined_description})' if show_descriptions else ''))
    if predefined != 0: return
    parse_descriptors(data, indent, namespace='QoS')

def parse_QoS_Qualifier_descriptor(data, indent: int):
    pass

def parse_BaseCommand_descriptor(data, indent: int):
    pass

descriptor_namespaces = {

    'default': {
        'classes': [
            { 'name': 'BaseDescriptor', 'base_class': None },

            { 'tag': 0x03, 'base_class': 'BaseDescriptor', 'name': 'ES_Descriptor', 'tag_name': 'ES_DescrTag' },
            { 'tag': 0x05, 'base_class': 'BaseDescriptor', 'name': 'DecoderSpecificInfo', 'tag_name': 'DecSpecificInfoTag' },
            { 'tag': 0x04, 'base_class': 'BaseDescriptor', 'name': 'DecoderConfigDescriptor', 'tag_name': 'DecoderConfigDescrTag' },
            { 'tag': 0x09, 'base_class': 'BaseDescriptor', 'name': 'IPI_DescrPointer', 'tag_name': 'IPI_DescrPointerTag' },
            { 'tag': 0x0a, 'base_class': 'BaseDescriptor', 'name': 'IPMP_DescriptorPointer', 'tag_name': 'IPMP_DescrPointerTag' },
            { 'tag': 0x0b, 'base_class': 'BaseDescriptor', 'name': 'IPMP_Descriptor', 'tag_name': 'IPMP_DescrTag' },
            { 'tag': 0x60, 'base_class': 'BaseDescriptor', 'name': 'IPMP_ToolListDescriptor', 'tag_name': 'IPMP_ToolsListDescrTag' },
            { 'tag': 0x61, 'base_class': 'BaseDescriptor', 'name': 'IPMP_Tool', 'tag_name': 'IPMP_ToolTag' },
            { 'tag': 0x0c, 'base_class': 'BaseDescriptor', 'name': 'QoS_Descriptor', 'tag_name': 'QoS_DescrTag' },
            { 'tag': 0x0d, 'base_class': 'BaseDescriptor', 'name': 'RegistrationDescriptor', 'tag_name': 'RegistrationDescrTag' },

            { 'name': 'ObjectDescriptorBase', 'base_class': 'BaseDescriptor' },
            { 'tag': 0x01, 'base_class': 'ObjectDescriptorBase', 'name': 'ObjectDescriptor', 'tag_name': 'ObjectDescrTag' },
            { 'tag': 0x02, 'base_class': 'ObjectDescriptorBase', 'name': 'InitialObjectDescriptor', 'tag_name': 'InitialObjectDescrTag' },
            { 'name': 'IP_IdentificationDataSet', 'base_class': 'BaseDescriptor' },
            { 'tag': 0x07, 'base_class': 'IP_IdentificationDataSet', 'name': 'ContentIdentificationDescriptor', 'tag_name': 'ContentIdentDescrTag' },
            { 'tag': 0x08, 'base_class': 'IP_IdentificationDataSet', 'name': 'SupplementaryContentIdentificationDescriptor', 'tag_name': 'SupplContentIdentDescrTag' },

            { 'name': 'OCI_Descriptor', 'base_class': 'BaseDescriptor' },
            { 'tag': 0x40, 'base_class': 'OCI_Descriptor', 'name': 'ContentClassificationDescriptor', 'tag_name': 'ContentClassificationDescrTag' },
            { 'tag': 0x41, 'base_class': 'OCI_Descriptor', 'name': 'KeyWordDescriptor', 'tag_name': 'KeyWordDescrTag' },
            { 'tag': 0x42, 'base_class': 'OCI_Descriptor', 'name': 'RatingDescriptor', 'tag_name': 'RatingDescrTag' },
            { 'tag': 0x43, 'base_class': 'OCI_Descriptor', 'name': 'LanguageDescriptor', 'tag_name': 'LanguageDescrTag' },
            { 'tag': 0x44, 'base_class': 'OCI_Descriptor', 'name': 'ShortTextualDescriptor', 'tag_name': 'ShortTextualDescrTag' },
            { 'tag': 0x45, 'base_class': 'OCI_Descriptor', 'name': 'ExpandedTextualDescriptor', 'tag_name': 'ExpandedTextualDescrTag' },
            { 'tag': 0x46, 'base_class': 'OCI_Descriptor', 'name': 'ContentCreatorNameDescriptor', 'tag_name': 'ContentCreatorNameDescrTag' },
            { 'tag': 0x47, 'base_class': 'OCI_Descriptor', 'name': 'ContentCreationDateDescriptor', 'tag_name': 'ContentCreationDateDescrTag' },
            { 'tag': 0x48, 'base_class': 'OCI_Descriptor', 'name': 'OCICreatorNameDescriptor', 'tag_name': 'OCICreatorNameDescrTag' },
            { 'tag': 0x49, 'base_class': 'OCI_Descriptor', 'name': 'OCICreationDateDescriptor', 'tag_name': 'OCICreationDateDescrTag' },
            { 'tag': 0x4a, 'base_class': 'OCI_Descriptor', 'name': 'SmpteCameraPositionDescriptor', 'tag_name': 'SmpteCameraPositionDescrTag' },
            { 'tag': 0x4b, 'base_class': 'OCI_Descriptor', 'name': 'SegmentDescriptor', 'tag_name': 'SegmentDescrTag' },
            { 'tag': 0x4c, 'base_class': 'OCI_Descriptor', 'name': 'MediaTimeDescriptor', 'tag_name': 'MediaTimeDescrTag' },

            { 'name': 'ExtensionDescriptor', 'base_class': 'BaseDescriptor' },
            { 'tag': 0x13, 'base_class': 'ExtensionDescriptor', 'name': 'ExtensionProfileLevelDescriptor', 'tag_name': 'ExtensionProfileLevelDescrTag' },
            { 'tag': 0x14, 'base_class': 'BaseDescriptor', 'name': 'ProfileLevelIndicationIndexDescriptor', 'tag_name': 'ProfileLevelIndicationIndexDescrTag' },

            { 'tag': 0x06, 'base_class': 'BaseDescriptor', 'name': 'SLConfigDescriptor', 'tag_name': 'SLConfigDescrTag' },
            { 'tag': 0x64, 'base_class': 'SLConfigDescriptor', 'name': 'ExtendedSLConfigDescriptor', 'tag_name': 'ExtSLConfigDescrTag' },
            { 'name': 'SLExtensionDescriptor', 'base_class': 'BaseDescriptor' },  # quirk, this class doesn't have a base class in the spec
            { 'tag': 0x67, 'base_class': 'SLExtensionDescriptor', 'name': 'DependencyPointer', 'tag_name': 'DependencyPointerTag' },
            { 'tag': 0x68, 'base_class': 'SLExtensionDescriptor', 'name': 'MarkerDescriptor', 'tag_name': 'DependencyMarkerTag' },

            { 'tag': 0x69, 'base_class': 'BaseDescriptor', 'name': 'M4MuxChannelDescriptor', 'tag_name': 'M4MuxChannelDescrTag' },
            { 'tag': 0x65, 'base_class': 'BaseDescriptor', 'name': 'M4MuxBufferSizeDescriptor', 'tag_name': 'M4MuxBufferSizeDescrTag' },
            { 'tag': 0x62, 'base_class': 'BaseDescriptor', 'name': 'M4MuxTimingDescriptor', 'tag_name': 'M4MuxTimingDescrTag' },
            { 'tag': 0x63, 'base_class': 'BaseDescriptor', 'name': 'M4MuxCodeTableDescriptor', 'tag_name': 'M4MuxCodeTableDescrTag' },
            { 'tag': 0x66, 'base_class': 'BaseDescriptor', 'name': 'M4MuxIdentDescriptor', 'tag_name': 'M4MuxIdentDescrTag' },

            # defined in ISO/IEC 14496-14. names for the last two are made up as not defined formally anywhere
            { 'tag': 0x0e, 'base_class': 'BaseDescriptor', 'name': 'ES_ID_Inc', 'tag_name': 'ES_ID_IncTag' },
            { 'tag': 0x0f, 'base_class': 'BaseDescriptor', 'name': 'ES_ID_Ref', 'tag_name': 'ES_ID_RefTag' },
            { 'tag': 0x11, 'base_class': 'ObjectDescriptor', 'name': '<MP4ObjectDescriptor>', 'tag_name': 'MP4_OD_Tag' },
            { 'tag': 0x10, 'base_class': 'InitialObjectDescriptor', 'name': '<MP4InitialObjectDescriptor>', 'tag_name': 'MP4_IOD_Tag' },

            # was unable to find where this is defined
            { 'tag': 0x12, 'base_class': 'BaseDescriptor', 'name': '<IPL_DescrPointerRef>', 'tag_name': 'IPL_DescrPointerRefTag' },
        ],
        'ranges': [
            (0x40, 0x60, 'OCI_Descriptor'),
            (0x6A, 0xFF, 'ExtensionDescriptor'),
        ],
        'user_private': 0xC0,
    },

    'command': {
        'classes': [
            { 'name': 'BaseCommand', 'base_class': None },

            { 'tag': 0x01, 'base_class': 'BaseCommand', 'name': 'ObjectDescriptorUpdate', 'tag_name': 'ObjectDescrUpdateTag' },
            { 'tag': 0x02, 'base_class': 'BaseCommand', 'name': 'ObjectDescriptorRemove', 'tag_name': 'ObjectDescrRemoveTag' },
            { 'tag': 0x03, 'base_class': 'BaseCommand', 'name': 'ES_DescriptorUpdate', 'tag_name': 'ES_DescrUpdateTag' },
            { 'tag': 0x04, 'base_class': 'BaseCommand', 'name': 'ES_DescriptorRemove', 'tag_name': 'ES_DescrRemoveTag' },
            { 'tag': 0x05, 'base_class': 'BaseCommand', 'name': 'IPMP_DescriptorUpdate', 'tag_name': 'IPMP_DescrUpdateTag' },
            { 'tag': 0x06, 'base_class': 'BaseCommand', 'name': 'IPMP_DescriptorRemove', 'tag_name': 'IPMP_DescrRemoveTag' },
            { 'tag': 0x08, 'base_class': 'BaseCommand', 'name': 'ObjectDescriptorExecute', 'tag_name': 'ObjectDescrExecuteTag' },

            # defined in ISO/IEC 14496-14. names is made up as not defined formally anywhere
            { 'tag': 0x07, 'base_class': 'ES_DescriptorRemove', 'name': '<ES_DescriptorRemoveRef>', 'tag_name': 'ES_DescrRemoveRefTag' },
        ],
        'user_private': 0xC0,
    },

    'QoS': {
        'classes': [
            { 'name': 'QoS_Qualifier', 'base_class': None },

            { 'tag': 0x01, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_MAX_DELAY' },
            { 'tag': 0x02, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_PREF_MAX_DELAY' },
            { 'tag': 0x03, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_LOSS_PROB' },
            { 'tag': 0x04, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_MAX_GAP_LOSS' },
            { 'tag': 0x41, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_MAX_AU_SIZE' },
            { 'tag': 0x42, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_AVG_AU_SIZE' },
            { 'tag': 0x43, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_MAX_AU_RATE' },
            { 'tag': 0x44, 'base_class': 'QoS_Qualifier', 'name': 'QoS_Qualifier_REBUFFERING_RATIO' },
        ],
        'user_private': 0x80,
    },

    'IPMP': {
        'classes': [
            { 'name': 'IPMP_Data_BaseClass', 'base_class': None },  # <- keep in mind this has fields

            { 'tag': 0x10, 'base_class': 'IPMP_Data_BaseClass', 'name': 'IPMP_ParamtericDescription', 'tag_name': 'IPMP_ParamtericDescription_tag' },

            # tag numbers defined in ISO/IEC 14496-13
            # FIXME: define them here, and set user_private
        ],
    },

}

def init_descriptors():
    global class_registry
    # do sanity checks on the data defined above. for every namespace, make sure:
    #  - class names are globally unique
    class_registry = unique_dict((k['name'], (nsname, k)) for nsname, ns in descriptor_namespaces.items() for k in ns['classes'])
    for nsname, ns in descriptor_namespaces.items():
        #  - there's exactly one root class
        #  - tags are unique
        ns['tag_registry'] = unique_dict(( k['tag'], k ) for k in ns['classes'] if 'tag' in k)
        #  - range class names are valid
        #  - base classes are valid, and there are no cycles
        for k in ns['classes']:
            while not MONITOR.abortRequested() and k['base_class'] != None:
                k = class_registry[k['base_class']][1]

    # register handlers defined above
    for k, v in globals().items():
        if m := re.fullmatch(r'parse_(.+)_descriptor', k):
            k = m.group(1)
            class_registry[k][1]['handler'] = v

    # check base classes of defined handlers also have a defined handler
    for k in class_registry.items():
        if 'handler' in k:
            while not MONITOR.abortRequested() and k['base_class'] != None:
                k = class_registry[k['base_class']][1]

init_descriptors()

object_types = {
    0x01: {                  'name': 'Systems ISO/IEC 14496-1',                                                                                         'notes': ['a'] },
    0x02: {                  'name': 'Systems ISO/IEC 14496-1',                                                                                         'notes': ['b'] },
    0x03: {                  'name': 'Interaction Stream',                                                                                                             },
    0x04: {                  'name': 'Extended BIFS',                                                                                                   'notes': ['h'] },
    0x05: {                  'name': 'AFX Stream',                                                                                                      'notes': ['i'] },
    0x06: { 'kind': 'font',  'name': 'Font Data Stream',                                                                                                               },
    0x07: {                  'name': 'Synthetised Texture',                                                                                                            },
    0x08: { 'kind': 'text',  'name': 'Text Stream',                                                                                                                    },
    0x09: {                  'name': 'LASeR Stream',                                                                                                                   },
    0x0A: {                  'name': 'Simple Aggregation Format (SAF) Stream',                                                                                         },

    0x20: { 'kind': 'video', 'name': 'Visual ISO/IEC 14496-2',                                            'short': 'MPEG-4 Video',                      'notes': ['c'] },
    0x21: { 'kind': 'video', 'name': 'Visual ITU-T Recommendation H.264 | ISO/IEC 14496-10',              'short': 'H.264 / AVC',                       'notes': ['g'] },
    0x22: { 'kind': 'video', 'name': 'Parameter Sets for ITU-T Recommendation H.264 | ISO/IEC 14496-10',  'short': 'H.264 / AVC (PPS / SPS)',           'notes': ['g'] },
    0x23: { 'kind': 'video', 'name': 'Visual ISO/IEC 23008-2 | ITU-T Recommendation H.265',               'short': 'H.265 / HEVC',                                     },

    0x40: { 'kind': 'audio', 'name': 'Audio ISO/IEC 14496-3',                                             'short': 'AAC',                               'notes': ['d'] },

    0x60: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 Simple Profile',                             'short': 'MPEG-2 Video (Simple Profile)',                    },
    0x61: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 Main Profile',                               'short': 'MPEG-2 Video (Main Profile)',                      },
    0x62: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 SNR Profile',                                'short': 'MPEG-2 Video (SNR Profile)',                       },
    0x63: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 Spatial Profile',                            'short': 'MPEG-2 Video (Spatial Profile)',                   },
    0x64: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 High Profile',                               'short': 'MPEG-2 Video (High Profile)',                      },
    0x65: { 'kind': 'video', 'name': 'Visual ISO/IEC 13818-2 422 Profile',                                'short': 'MPEG-2 Video (422 Profile)',                       },
    0x66: { 'kind': 'audio', 'name': 'Audio ISO/IEC 13818-7 Main Profile',                                'short': 'MPEG-2 AAC',                                       },
    0x67: { 'kind': 'audio', 'name': 'Audio ISO/IEC 13818-7 LowComplexity Profile',                       'short': 'MPEG-2 AAC-LC',                                    },
    0x68: { 'kind': 'audio', 'name': 'Audio ISO/IEC 13818-7 Scaleable Sampling Rate Profile',             'short': 'MPEG-2 AAC-SSR',                                   },
    0x69: { 'kind': 'audio', 'name': 'Audio ISO/IEC 13818-3',                                             'short': 'MPEG-2 BC Audio',                                  },
    0x6A: { 'kind': 'video', 'name': 'Visual ISO/IEC 11172-2',                                            'short': 'MPEG-1 Video',                                     },
    0x6B: { 'kind': 'audio', 'name': 'Audio ISO/IEC 11172-3',                                             'short': 'MPEG-1 Audio (usually MP3)',                       },
    0x6C: { 'kind': 'image', 'name': 'Visual ISO/IEC 10918-1',                                            'short': 'JPEG',                                             },
    0x6D: { 'kind': 'image', 'name': 'Portable Network Graphics',                                         'short': 'PNG',                               'notes': ['f'] },
    0x6E: { 'kind': 'image', 'name': 'Visual ISO/IEC 15444-1 (JPEG 2000)',                                'short': 'JPEG 2000',                                        },

    0xA0: { 'kind': 'audio', 'name': 'EVRC Voice',                                                                                                                     },
    0xA1: { 'kind': 'audio', 'name': 'SMV Voice',                                                                                                                      },
    0xA2: {                  'name': '3GPP2 Compact Multimedia Format (CMF)',                             'short': 'CMF',                                              },
    0xA3: { 'kind': 'video', 'name': 'SMPTE VC-1 Video',                                                                                                               },
    0xA4: { 'kind': 'video', 'name': 'Dirac Video Coder',                                                                                                              },
    0xA5: { 'kind': 'audio', 'name': 'AC-3',                                                              'withdrawn': True,                                           },
    0xA6: { 'kind': 'audio', 'name': 'Enhanced AC-3',                                                     'withdrawn': True,                                           },
    0xA7: { 'kind': 'audio', 'name': 'DRA Audio',                                                                                                                      },
    0xA8: { 'kind': 'audio', 'name': 'ITU G.719 Audio',                                                                                                                },
    0xA9: {                  'name': 'Core Substream',                                                                                                                 },
    0xAA: {                  'name': 'Core Substream + Extension Substream',                                                                                           },
    0xAB: {                  'name': 'Extension Substream containing only XLL',                                                                                        },
    0xAC: {                  'name': 'Extension Substream containing only LBR',                                                                                        },
    0xAD: { 'kind': 'audio', 'name': 'Opus audio',                                                        'short': 'Opus',                                             },
    0xAE: { 'kind': 'audio', 'name': 'AC-4',                                                              'withdrawn': True,                                           },
    0xAF: { 'kind': 'audio', 'name': 'Auro-Cx 3D audio',                                                                                                               },
    0xB0: { 'kind': 'video', 'name': 'RealVideo Codec 11',                                                                                                             },
    0xB1: { 'kind': 'video', 'name': 'VP9 Video',                                                         'short': 'VP9',                                              },
    0xB2: { 'kind': 'audio', 'name': 'DTS-UHD profile 2',                                                                                                              },
    0xB3: { 'kind': 'audio', 'name': 'DTS-UHD profile 3 or higher',                                                                                                    },

    0xE1: { 'kind': 'audio', 'name': '13K Voice',                                                                                                                      },
}

def format_object_type(oti: int) -> str:
    if oti == 0x00:
        raise AssertionError('forbidden object type')
    elif oti == 0xFF:
        return ansi_dim('no object type specified')
    elif e := (object_types.get(oti)):
        description = e.get('short') or e['name']
        if e.get('withdrawn'):
            description += ansi_fg1(' (withdrawn, unused, do not use)')
        return description
    else:
        return ansi_fg4('reserved for ISO use' if oti < 0xC0 else 'user private')

stream_types = {
    0x01: 'ObjectDescriptorStream',
    0x02: 'ClockReferenceStream',
    0x03: 'SceneDescriptionStream',
    0x04: 'VisualStream',
    0x05: 'AudioStream',
    0x06: 'MPEG7Stream',
    0x07: 'IPMPStream',
    0x08: 'ObjectContentInfoStream',
    0x09: 'MPEGJStream',
    0x0A: 'Interaction Stream',
    0x0B: 'IPMPToolStream',
    0x0C: 'FontDataStream',
    0x0D: 'StreamingText',
}

def format_stream_type(sti: int) -> str:
    if sti == 0x00:
        raise AssertionError('forbidden stream type')
    elif e := (stream_types.get(sti)):
        return e
    else:
        return ansi_fg4('reserved for ISO use' if sti < 0x20 else 'user private')

        
class MP4ParserNew:
    def determineLength(self, filename):
        log("MP4ParserNew: determineLength " + filename)
        try: self.File = FileAccess.open(filename, "rb", None)
        except:
            log("MP4ParserNew: Unable to open the file")
            return
        try:
            parse_boxes(0, self.File.readBytes())
            dur = round(sum(durations) / len(durations))
            log("MP4ParserNew: Duration is %s"%(dur))
            self.File.close()
            return dur
        except Exception as e:
            log("MP4ParserNew: failed! %s"%(e))
            return 0

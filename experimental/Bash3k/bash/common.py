import codecs
import locale
import os
from collections import OrderedDict
bom_encoding_dict = {codecs.BOM_UTF8 : 'UTF8',
                     codecs.BOM_UTF16_LE : 'UTF-16LE',
                     codecs.BOM_UTF16_BE : 'UTF-16BE',
                     codecs.BOM_UTF32_LE : 'UTF-32LE',
                     codecs.BOM_UTF32_BE : 'UTF-32BE'}
max_bom_length = max([len(bom) for bom in bom_encoding_dict.keys()])

def read_text_file(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    #Check to see if a Byte Order Marker is present
    bom_length = max_bom_length
    bom = data[:max_bom_length]
    successful_encoding = None

    #Chop off the potential BOM one byte at a time to test for matches
    while successful_encoding is None and bom_length > 0:
        bom = bom[:bom_length]
        successful_encoding = bom_encoding_dict.get(bom, None)
        bom_length -= 1

    if successful_encoding: #BOM found, life is easy
        #Strip the BOM from the data since some codecs don't handle it gracefully
        try:
            text = str(data[len(bom):], encoding=successful_encoding, errors='strict')
        except UnicodeError as e:
            raise UnicodeError('%s\n\nUnable to decode file (%s). A Byte Order Marker for (%s) was found, but it didn\'t work.' % (e, filename, successful_encoding))
        return text

    #Life isn't so easy. Guess at an encoding.

    #Hack
    #Not sure, but I don't believe null bytes should ever be present in an utf-8 encoded file
    #To be somewhat safe, assume it isn't utf-8 if more null bytes are encountered than an arbitrary limit
    null_count = 0
    for byte in data:
        if byte == 0:
            null_count += 1
            if null_count > 10:
                encodings = ['utf-16']
                break
    else:
        encodings = ['utf-8','utf-16']

    # next we add anything we can learn from the locale
    try:
        encodings.append(locale.nl_langinfo(locale.CODESET))
    except AttributeError:
        pass
    try:
        encodings.append(locale.getlocale()[1])
    except (AttributeError, IndexError):
        pass
    try:
        encodings.append(locale.getdefaultlocale()[1])
    except (AttributeError, IndexError):
        pass
    # we try 'latin-1' last
    encodings.append('latin-1')

    for enc in encodings:
        # some of the locale calls
        # may have returned None
        if not enc: continue
        try:
            print('trying %s' % (enc,))
            return str(data, encoding=enc, errors='strict')
        except (UnicodeError, LookupError) as e:
            print('\t',e)
            pass
    raise UnicodeError('Unable to decode input data. Tried the following encodings: %s.' % ', '.join([repr(enc) for enc in encodings if enc]))

def norm_path(filepath):
    return os.path.expandvars(os.path.normpath(filepath))

def norm_join(*args):
    return norm_path(os.path.join(*args))

def load_ini_settings(filename, bash_vars={}):
    from bash.common import read_text_file
    import configparser
    config = configparser.RawConfigParser(default_section='Common',delimiters=('=',))
    config.optionxform = str #make keys case sensitive
    config_text = read_text_file(filename)
    config.read_string(config_text)
    sanitized_options = OrderedDict() #So that writing the values out later occur in the same order they were read

    def _coerce(value, newtype, base=None, AllowNone=False):
        try:
            if newtype is float:
                import struct
                pack,unpack = struct.pack,struct.unpack
                return round(unpack('f',pack('f',float(value)))[0], 6) #--Force standard precision
            if newtype is bool:
                if isinstance(value, str):
                    retValue = value.strip().lower()
                    if AllowNone and retValue == 'none': return None
                    return not retValue in ('','none','false','no','0','0.0')
                return bool(newtype)
            if base: retValue = newtype(value, base)
            else: retValue = newtype(value)
            if AllowNone and isinstance(retValue, str) and retValue.lower() == 'none':
                return None
            return retValue
        except (ValueError, TypeError):
            if newtype is int: return 0
            return None
    def replace_bash_vars(path_str, bash_vars):
        for key, value in bash_vars.items():
            path_str = path_str.replace(key, value)
        return path_str
    type_sanitizer = {'s':lambda x: _coerce(x, str),
                      'sl':lambda x: _coerce(x, str).split(';'),
                      'b':lambda x: _coerce(x, bool),
                      'i':lambda x: _coerce(x, int),
                      'f':lambda x: _coerce(x, float),
                      'p':lambda x, _bash_vars=bash_vars: replace_bash_vars(_coerce(x, str), _bash_vars)}
    for section in config.sections():
        options = config.items(section)
        for key, value in options:
            key_type, sep, key = key.partition('_')
            sanitized_options['%s.%s' % (section, key)] = type_sanitizer[key_type](value)
    return sanitized_options

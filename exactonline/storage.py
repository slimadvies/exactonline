# vim: set ts=8 sw=4 sts=4 et ai tw=79:
"""
Provides a storage class to the Exact Online REST API Library.

This file is part of the Exact Online REST API Library in Python
(EORALP), licensed under the LGPLv3+.
Copyright (C) 2015 Walter Doekes, OSSO B.V.

Usage:

    storage = IniStorage('somefile.ini')

Or, if you want to use your own storage backend, you may provide a set()
and get() method and inherit from the ExactOnlineConfig.

    class MyStorage(ExactOnlineConfig):
        def get(self, section, option):
            try:
                return self.fetch_stuff_from_somewhere(...)
            except:
                raise NoOptionError()

        def set(self, section, option, value):
            self.store_stuff_somewhere(...)

Example ini file:

    [server]
    auth_url = https://start.exactonline.co.uk/api/oauth2/auth
    rest_url = https://start.exactonline.co.uk/api
    token_url = https://start.exactonline.co.uk/api/oauth2/token

    [application]
    base_url = https://example.com
    client_id = {12345678-abcd-1234-abcd-0123456789ab}
    client_secret = ZZZ999xxx000

    [transient]
    access_expiry = 1426492503
    access_token = dAfjGhB1k2tE2dkG12sd1Ff1A1fj2fH2Y1j1fKJl2f1sD1ON275zJNUy...
    code = dAfj!hB1k2tE2dkG12sd1Ff1A1fj2fH2Y1j1fKJl2f1sD1ON275zJNUy...
    division = 123456
    refresh_token = SDFu!12SAah-un-56su-1fj2fH2Y1j1fKJl2f1sDfKJl2f1sD11FfUn1...

"""
from unittest import TestCase, main
from io import StringIO
from os import path, unlink

try:
    from configparser import NoSectionError, NoOptionError, ConfigParser
except ImportError:  # python2
    from configparser import (
        NoSectionError, NoOptionError,
        SafeConfigParser as ConfigParserOldStyle)

    class ConfigParser(ConfigParserOldStyle, object):
        """
        We require this adapter to upgrade the RawConfigParser to a
        new-style class. Only needed in Python2.
        """
        def __init__(self, **kwargs):
            # Must call this __init__ manually :(
            ConfigParserOldStyle.__init__(self, **kwargs)
            super(ConfigParser, self).__init__(**kwargs)


# TODO: replace NoOptionError with a custom/own config error?
# TODO: move the exactonlineconfig base to a separate file one doesn't need to
# import from the ConfigParser?


class ExactOnlineConfig(object):
    def get_or_set_default(self, section, option, value):
        """
        Base method to fetch values and to set defaults in case they
        don't exist.
        """
        try:
            ret = self.get(section, option)
        except (NoOptionError, NoSectionError):
            self.set(section, option, value)
            ret = value

        return ret

    # [server]
    # ; These always return something. They may write their default to
    # ; your config object if they are unset.
    # ; If you want to change the values from your application, you need
    # ; to write your own routines.

    def get_auth_url(self):
        return self.get_or_set_default(
            'server', 'auth_url',
            'https://start.exactonline.nl/api/oauth2/auth')

    def get_rest_url(self):
        return self.get_or_set_default(
            'server', 'rest_url',
            'https://start.exactonline.nl/api')

    def get_token_url(self):
        return self.get_or_set_default(
            'server', 'token_url',
            'https://start.exactonline.nl/api/oauth2/token')

    # [application]
    # ; These return something, or raise NoOptionError if they are
    # ; unset.
    # ; If you want to change the values from your application, you need
    # ; to write your own routines.

    def get_base_url(self):
        return self.get('application', 'base_url')

    def get_client_id(self):
        return self.get('application', 'client_id')

    def get_client_secret(self):
        return self.get('application', 'client_secret')

    # [transient]
    # ; These return something, or raise NoOptionError if they are
    # ; unset.
    # ; These will be written to by this exactonline library, so all
    # ; their get methods have set counterparts.

    def get_access_expiry(self):
        return int(self.get('transient', 'access_expiry'))

    def set_access_expiry(self, value):
        self.set('transient', 'access_expiry', str(value))

    def get_access_token(self):
        return self.get('transient', 'access_token')

    def set_access_token(self, value):
        self.set('transient', 'access_token', value)

    def get_code(self):
        return self.get('transient', 'code')

    def set_code(self, value):
        self.set('transient', 'code', value)

    def get_division(self):
        return int(self.get('transient', 'division'))

    def set_division(self, value):
        self.set('transient', 'division', str(value))

    def get_refresh_token(self):
        return self.get('transient', 'refresh_token')

    def set_refresh_token(self, value):
        self.set('transient', 'refresh_token', value)

    # ; aliases

    def get_refresh_url(self):
        "Alias for get_token_url()."
        return self.get_token_url()


class IniStorage(ExactOnlineConfig, ConfigParser):
    """
    Configuration based on the SafeConfigParser and the
    ExactOnlineConfig.

    Takes a ``filename_or_fp`` which can either be a filename or a file
    pointer. If it is a filename, all set() operations are destructive:
    the file will be automatically updated.
    """
    def __init__(self, filename_or_fp, **kwargs):
        super(IniStorage, self).__init__(**kwargs)

        if hasattr(filename_or_fp, 'read'):
            if hasattr(self, 'read_file'):
                self.read_file(filename_or_fp)
            else:
                self.readfp(filename_or_fp)  # python<3.2
            self.overwrite = False
        else:
            self.read(filename_or_fp)
            self.overwrite = filename_or_fp

    def get(self, section, option, **kwargs):
        """
        Get method that raises NoOptionError if the value was unset.
        This differs from the SafeConfigParser which may also raise a
        NoSectionError.
        """
        try:
            ret = super(ExactOnlineConfig, self).get(section, option, **kwargs)
        except NoSectionError:
            raise NoOptionError(option, section)
        return ret

    def set(self, section, option, value):
        """
        Set method that (1) auto-saves if possible and (2) auto-creates
        sections.
        """
        try:
            super(ExactOnlineConfig, self).set(section, option, value)
        except NoSectionError:
            self.add_section(section)
            super(ExactOnlineConfig, self).set(section, option, value)

        # Save automatically!
        self.save()

    def save(self):
        if self.overwrite:
            with open(self.overwrite, 'w') as output:
                self.write(output)


class IniStorageTestCase(TestCase):
    def test_dont_die_if_config_doesnt_exist(self):
        try:
            config = IniStorage('storage-does-not-exist.ini')
            del config
            self.assertFalse(path.exists('storage-does-not-exist.ini'))
        finally:
            try:
                unlink('storage-does-not-exist.ini')
            except OSError:
                pass

    def test_missing_section_raises_nooption(self):
        config = IniStorage(StringIO())
        self.assertRaises(NoOptionError, config.get, 'bad_section',
                          'bad_value')

    def test_server_defaults(self):
        config = IniStorage(StringIO())
        self.assertEqual(config.get_auth_url(),
                         'https://start.exactonline.nl/api/oauth2/auth')
        self.assertEqual(config.get_rest_url(),
                         'https://start.exactonline.nl/api')
        self.assertEqual(config.get_token_url(),
                         'https://start.exactonline.nl/api/oauth2/token')

    def test_server_default_writes(self):
        try:
            self.assertFalse(path.exists('storage-gets-created.ini'))
            config = IniStorage('storage-gets-created.ini')
            auth_url = 'https://start.exactonline.nl/api/oauth2/auth'
            self.assertEqual(config.get_auth_url(), auth_url)
            with open('storage-gets-created.ini', 'r') as written:
                for line in written:
                    if auth_url in line:
                        break
                else:
                    self.assertFalse('URL %r not found in file' % (auth_url,))
        finally:
            try:
                unlink('storage-gets-created.ini')
            except OSError:
                pass

    def test_application_no_defaults(self):
        config = IniStorage(StringIO())
        self.assertRaises(NoOptionError, config.get_base_url)
        self.assertRaises(NoOptionError, config.get_client_id)
        self.assertRaises(NoOptionError, config.get_client_secret)

    def test_transient_no_defaults(self):
        config = IniStorage(StringIO())
        self.assertRaises(NoOptionError, config.get_access_expiry)
        self.assertRaises(NoOptionError, config.get_access_token)
        self.assertRaises(NoOptionError, config.get_code)
        self.assertRaises(NoOptionError, config.get_division)
        self.assertRaises(NoOptionError, config.get_refresh_token)

    def test_example_ini(self):
        config = IniStorage(path.join(path.dirname(__file__), 'example.ini'))

        # [server]
        self.assertEqual(config.get_auth_url(),
                         'https://start.exactonline.co.uk/api/oauth2/auth')
        self.assertEqual(config.get_rest_url(),
                         'https://start.exactonline.co.uk/api')
        self.assertEqual(config.get_token_url(),
                         'https://start.exactonline.co.uk/api/oauth2/token')
        self.assertEqual(config.get_token_url(), config.get_refresh_url())

        # [application]
        self.assertEqual(config.get_base_url(), 'https://example.com')
        self.assertEqual(config.get_client_id(),
                         '{12345678-abcd-1234-abcd-0123456789ab}')
        self.assertEqual(config.get_client_secret(), 'ZZZ999xxx000')

        # [transient]
        self.assertEqual(config.get_access_expiry(), 1426492503)
        self.assertEqual(
            config.get_access_token(),
            'dAfjGhB1k2tE2dkG12sd1Ff1A1fj2fH2Y1j1fKJl2f1sD1ON275zJNUy...')
        self.assertEqual(
            config.get_code(),
            'dAfj!hB1k2tE2dkG12sd1Ff1A1fj2fH2Y1j1fKJl2f1sD1ON275zJNUy...')
        self.assertEqual(config.get_division(), 123456)
        self.assertEqual(
            config.get_refresh_token(),
            'SDFu!12SAah-un-56su-1fj2fH2Y1j1fKJl2f1sDfKJl2f1sD11FfUn1...')

    def test_transient_writes(self):
        try:
            self.assertFalse(path.exists('storage-gets-created.ini'))
            config = IniStorage('storage-gets-created.ini')
            self.assertRaises(NoOptionError, config.get_division)
            config.set_division(987654321)
            self.assertEqual(config.get_division(), 987654321)
            config.set_division(11223344)

            # Re-open config, and check availability.
            config2 = IniStorage('storage-gets-created.ini')
            self.assertEqual(config2.get_division(), 11223344)
        finally:
            try:
                unlink('storage-gets-created.ini')
            except OSError:
                pass


if __name__ == '__main__':
    main()

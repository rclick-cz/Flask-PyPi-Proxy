# -*- coding: utf-8 -*-

''' Handles downloading a package file.

This is called by easy_install or pip after calling the simple, and getting
the version of the package to download.

'''

import magic
from flask import make_response, request, abort
from flask_pypi_proxy.app import app
from flask_pypi_proxy.utils import (get_base_path, get_package_path,
                                    get_md5_for_content)
from os import makedirs
from os.path import join, exists
from requests import get, head
# from subprocess import Popen


@app.route('/packages/source/<source_letter>/<package_name>/<package_file>',
           methods=['GET', 'HEAD'])
def package(source_letter, package_name, package_file):
    ''' Downloads the egg

    :param str source_letter: the first char of the package name. For example:
                              D
    :param str package_name: the name of the package. For example: Django
    :param str package_file: the name of the package and it's version. For
                             example: Django==1.5.0
    '''
    egg_filename = join(get_base_path(), package_name, package_file)
    if request.method == 'HEAD':
        # in this case the content type of the file is what is
        # required
        if not exists(egg_filename):
            url = app.config['PYPI_URL'] + 'packages/source/%s/%s/%s' % (
                                        source_letter,
                                        package_name,
                                        package_file)
            pypi_response = head(url)
            return _respond(pypi_response.content, pypi_response.headers['content-type'])

        else:
            mimetype = magic.from_file(egg_filename, mime=True)
            return _respond('', mimetype)

    app.logger.debug('Downloading: %s', package_file)
    if exists(egg_filename):
        app.logger.debug('Found local file in repository for: %s', package_file)
        # if the file exists, then use the local file.
        path = get_package_path(package_name)
        path = join(path, package_file)
        with open(path, 'rb') as egg:
            content = egg.read(-1)
        mimetype = magic.from_file(egg_filename, mime=True)
        return _respond(content, mimetype)

    else:
        # Downloads the egg from pypi and saves it locally, then
        # it will return it.

        # TODO: there are some problem here with some packages. For
        #       example: py-bcrypt

        package_path = get_package_path(package_name)
        url = app.config['PYPI_URL'] + 'packages/source/%s/%s/%s' % (
                                        source_letter,
                                        package_name,
                                        package_file)
        app.logger.debug('Starting to download: %s using the url: %s',
                         package_file, url)
        pypi_response = get(url)
        app.logger.debug('Finished downloading package: %s', package_file)

        if pypi_response.status_code != 200:
            app.logger.warning('Error respose while downloading for proxy: %s'
                               'Response details: %s', package_file,
                               pypi_response.text)
            abort(pypi_response.status_code)

        if not exists(package_path):
            makedirs(package_path)

        with open(egg_filename, 'w') as egg_file:
            egg_file.write(pypi_response.content)

        with open(egg_filename) as egg_file:
            filecontent = egg_file.read(-1)
            mimetype = magic.from_file(egg_filename, mime=True)

        with open(egg_filename + '.md5', 'w') as md5_output:
            md5 = get_md5_for_content(filecontent)
            md5_output.write(md5)

        return _respond(filecontent, mimetype)


def _respond(filecontent, mimetype):
    return make_response(filecontent, 200, {
                        'Content-Type': mimetype
                    }
            )
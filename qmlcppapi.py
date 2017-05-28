#!/usr/bin/env python3

# This is part of the QMLCppAPI project
# Copyright (C) 2017 Pelagicore AB
# SPDX-License-Identifier: LGPL-2.1
# This file is subject to the terms of the LGPL 2.1 license.
# Please see the LICENSE file for details. 

import click
from qface.generator import FileSystem, Generator
from path import Path
import logging
import logging.config
import yaml

here = Path(__file__).dirname()

logging.config.dictConfig(yaml.load(open(here / 'qface/log.yaml')))
log = logging.getLogger(__name__)


def parameterType(symbol):
    return symbol


def fullyQualifiedPath(symbol):
    return symbol.qualified_name.replace('.', '/')


def fullyQualifiedName(symbol):
    return symbol.qualified_name


def fullyQualifiedCppName(type):
    try:
        if type.is_primitive:
            return "::" + type.name
    except AttributeError:
        pass
    return '::{0}'.format(fullyQualifiedName(type)).replace(".", "::")


def namespaceOpen(symbol):
    parts = symbol.qualified_name.split('.')
    ns = ' '.join(['namespace %s {' % x for x in parts])
    return ns


def namespaceClose(symbol):
    parts = symbol.qualified_name.split('.')
    ns = '} ' * len(parts)
    return ns


def returnTypeFromSymbol(symbol):
    if symbol.is_void or symbol.is_primitive:
        if symbol.name == 'string':
            return 'QString'
        if symbol.name == 'real':
            return 'float'
        return symbol
    elif symbol.is_list:
        return 'QList<{0}>'.format(returnTypeFromSymbol(symbol.nested))
    else:
        return fullyQualifiedCppName(symbol)


def returnType(symbol):
    return returnTypeFromSymbol(symbol.type)


def returnQMLType(symbol):
    return symbol


def nestedType(symbol):
    return symbol.type.nested


def requiredIncludeFromType(symbol):
    typeName = ''
    if not symbol.is_primitive:
        symbol = symbol.nested if symbol.nested else symbol
        typeName = fullyQualifiedCppName(symbol)
        if typeName.startswith("::"):
            typeName = typeName[2:]
        return '#include "' + typeName.replace('::', '/') + '.h"'
    else:
        return ""


def requiredInclude(symbol):
    if not symbol.type.is_primitive:
        type = symbol.type.nested if symbol.type.nested else symbol.type
        return requiredIncludeFromType(type)
    return ""


def run_generation(input, output):
    system = FileSystem.parse(input)
    generator = Generator(search_path=Path(here / 'templates'))
    generator.register_filter('returnType', returnType)
    generator.register_filter('returnQMLType', returnQMLType)
    generator.register_filter('parameterType', parameterType)
    generator.register_filter('nestedType', nestedType)
    generator.register_filter('requiredInclude', requiredInclude)
    generator.register_filter('namespaceOpen', namespaceOpen)
    generator.register_filter('namespaceClose', namespaceClose)
    generator.register_filter('fullyQualifiedName', fullyQualifiedName)
    generator.register_filter('fullyQualifiedCppName', fullyQualifiedCppName)
    generator.register_filter('fullyQualifiedPath', fullyQualifiedPath)
    generator.destination = output

    ctx = {'output': output}
    for module in system.modules:
        ctx.update({'module': module})
        module_path = '/'.join(module.name_parts)
        log.debug('process module %s' % module.module_name)
        ctx.update({'path': module_path})
        generator.write('api/{{path}}/{{module|upperfirst}}Module.h', 'module.h', ctx)
        generator.write('api/{{path}}/{{module|upperfirst}}Module.cpp', 'module.cpp', ctx)
        generator.write('ipc/{{path}}/{{module|upperfirst}}ModuleIPC.h', 'moduleIPC.h', ctx)
        generator.write('dummy/{{path}}/{{module|upperfirst}}ModuleDummy.h', 'dummymodule.h', ctx)
        for interface in module.interfaces:
            log.debug('process interface %s' % interface)
            ctx.update({'interface': interface})
            generator.write('api/{{path}}/{{interface}}.h', 'service.h', ctx)
            generator.write('api/{{path}}/{{interface}}.cpp', 'service.cpp', ctx)
            generator.write('api/{{path}}/{{interface}}PropertyAdapter.h', 'serviceWithProperties.h', ctx)
            generator.write('api/{{path}}/{{interface}}QML.h', 'QMLImplementation.h', ctx)
            generator.write('api/{{path}}/{{interface}}QMLFrontend.h', 'QMLFrontend.h', ctx)
            generator.write('dummy/{{path}}/{{interface}}Dummy.h', 'dummyservice.h', ctx)
            generator.write('ipc/{{path}}/{{interface}}IPC.h', 'serviceIPC.h', ctx)
        for enum in module.enums:
            ctx.update({'enum': enum})
            generator.write('api/{{path}}/{{enum}}.h', 'enum.h', ctx)
            generator.write('api/{{path}}/{{enum}}.cpp', 'enum.cpp', ctx)
        for struct in module.structs:
            ctx.update({'struct': struct})
            generator.write('api/{{path}}/{{struct}}.h', 'struct.h', ctx)
            generator.write('api/{{path}}/{{struct}}.cpp', 'struct.cpp', ctx)


@click.command()
@click.argument('input', nargs=-1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path(exists=True))
def generate(input, output):
    """Takes several files or directories as input and generates the code
    in the given output directory."""
    run_generation(input, output)


if __name__ == '__main__':
    generate()

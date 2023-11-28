import os
import ast
import xml.etree.ElementTree as ET
import logging
_logger = logging.getLogger(__name__)

OPERATORS_MAPPING = {
    '!=': '!=',
    '=': '==',
    'in': 'in',
    'not in': 'not in',
}


def find_and_print_attrs(xml_file_path):
    modified_attrs = {}
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for elem in root.iter():
            if 'attrs' in elem.attrib and elem.attrib['attrs']:
                # Parse elem.attrib['attrs'] to get new attributes
                attributes = parse_attributes(elem.attrib['attrs'], xml_file_path)
                # Add new attributes readonly="True"
                for attribute in attributes:
                    elem.attrib[attribute] = attributes[attribute]
                # Delete deprecated attribute
                del elem.attrib['attrs']

                # Save modified attrs
                modified_attrs[xml_file_path] = attributes
        try:
            tree.write(xml_file_path)
        except:
            _logger.error("Failed to write tree in file %s" % xml_file_path)
    except ET.ParseError:
        pass
    return modified_attrs


def parse_attributes(attributes, xml_file_path):
    attributes = ast.literal_eval(attributes)
    for attribute in attributes:
        if isinstance(attributes[attribute], bool):
            attributes[attribute] = str(int(attributes[attribute]))
        elif isinstance(attributes[attribute], list):
            expession = get_expression(attributes[attribute], xml_file_path)
            attributes[attribute] = expession
        else:
            _logger.info('Undefined expression %s in %s' % (
                attributes[attribute],
                xml_file_path))

    return attributes


def get_expression(domain, xml_file_path):
    try:
        expression = ""
        # assert len(domain) == 3, 'domain %s in file %s is not valid' % (domain, xml_file_path)
        for expr in domain:
            expression += '%s %s %s' % (
                expr[0],
                OPERATORS_MAPPING.get(expr[1]),
                repr(expr[2]))
        print(domain, '->>>>>', expression)
    except Exception:
        _logger.info('Domain lenght is not valid %s' % domain)
    return expression

def search_in_folders(root_folder):
    attrs = {}
    for foldername, subfolders, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.endswith('.xml'):
                file_path = os.path.join(foldername, filename)
                xml_attrs = find_and_print_attrs(file_path)
                if xml_attrs:
                    attrs.update(xml_attrs)
    return attrs

attrs = search_in_folders('%s/crnd-inc/generic-addons' % os.path.dirname(
    os.getcwd()))
print(attrs)

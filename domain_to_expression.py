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


def find_and_replace_attrs(xml_file_path):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for elem in root.iter():
            # Check if element has attrs in attributes
            if 'attrs' in elem.attrib and elem.attrib['attrs']:
                # Parse attrs to split them on separate attributes
                # and evaluate expression of them
                attributes = parse_attributes(elem.attrib['attrs'], xml_file_path)
                # Add separate attributes
                for attribute in attributes:
                    elem.attrib[attribute] = attributes[attribute]
                # Delete deprecated attribute
                del elem.attrib['attrs']
        # Save modified attrs
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
    except ET.ParseError:
        _logger.error("Error parse file %s", xml_file_path)


def parse_attributes(attributes, xml_file_path):
    attributes = ast.literal_eval(attributes)
    for attribute in attributes:
        if isinstance(attributes[attribute], bool):
            attributes[attribute] = str(int(attributes[attribute]))
        elif isinstance(attributes[attribute], list):
            expession = get_expression(attributes[attribute], xml_file_path)
            if expession:
                attributes[attribute] = expession
        else:
            _logger.info('Undefined expression %s in %s' % (
                attributes[attribute],
                xml_file_path))

    return attributes


def get_expression(domain, xml_file_path):
    if len(domain) == 1:
        expression = ""
        for expr in domain:
            expression += '%s %s %s' % (
                expr[0],
                OPERATORS_MAPPING.get(expr[1]),
                repr(expr[2]))
        print(domain, '->>>>>', expression)
        return expression
    print('There is multiple domain %s in path %s. Passed.' % (
        domain, xml_file_path))
    return False


def search_in_folders(root_folder):
    for foldername, subfolders, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.endswith('.xml'):
                file_path = os.path.join(foldername, filename)
                find_and_replace_attrs(file_path)


search_in_folders('%s/crnd-inc/generic-addons' % os.path.dirname(os.getcwd()))

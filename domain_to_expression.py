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
    '|': ' or ',
    '&': ' and ',
}
DONE_CONVERT = 0
MISSED_CONVERT = 0


def find_and_replace_attrs(xml_file_path):
    global DONE_CONVERT
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
        DONE_CONVERT += 1
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
    global MISSED_CONVERT
    if len(domain) == 1 and isinstance(domain[0], tuple):
        expression = '%s %s %s' % (
            domain[0][0],
            OPERATORS_MAPPING.get(domain[0][1]),
            repr(domain[0][2]))
        print(domain, '->>>>>', expression)
        return expression
    else:
        operator = ' and '
        if all(isinstance(item, tuple) for item in domain):
            expr = [get_expression([expr], xml_file_path) for expr in domain]
            expression = operator.join(expr)
            print(domain, '->>>>>', expression)
            return expression
        else:
            print('There is multiple domain %s in path %s. Passed.' % (
                domain, xml_file_path))
            MISSED_CONVERT += 1
            return False


def search_in_folders(root_folder):
    for foldername, subfolders, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.endswith('.xml'):
                file_path = os.path.join(foldername, filename)
                find_and_replace_attrs(file_path)


search_in_folders('%s/crnd-inc/generic-addons' % os.path.dirname(os.getcwd()))
print('Done converted', DONE_CONVERT)
print('Missed converted', MISSED_CONVERT)

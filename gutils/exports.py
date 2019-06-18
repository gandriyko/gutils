# -*- coding: utf-8 -*-
from django.utils.encoding import smart_bytes
from django.template.loader import render_to_string
from pyexcelerate import Workbook
from xlwt import Workbook as WorkbookOld
from gutils.decimals import to_decimal
import tempfile
import datetime
import re
import io


def export_to_file(**kwargs):
    RE_DECIMAL = re.compile(r'^decimal:([\d\.\,]+)$')
    RE_INTEGER = re.compile(r'^integer:(\d+)$')
    RE_DATE = re.compile(r'^date:(.+)$')
    RE_DATETIME = re.compile(r'^datetime:(.+)$')

    def _process_line(line):
        result = []
        for item in line.split(';'):
            r = RE_DECIMAL.match(item)
            if r:
                result.append(to_decimal(r.group(1)))
                continue
            r = RE_INTEGER.match(item)
            if r:
                result.append(int(r.group(1)))
                continue
            r = RE_DATE.match(item)
            if r:
                dt = datetime.datetime.strptime(r.group(1), '%Y-%m-%d').date()
                result.append(dt)
            r = RE_DATETIME.match(item)
            if r:
                dt = datetime.datetime.strptime(r.group(1), '%Y-%m-%d %H:%M:%S')
                result.append(dt)
                continue
            result.append(item)
        return result

    encoding = kwargs.get('encoding') or 'utf-8'
    template = kwargs['template']
    file_name = kwargs.get('file_name')
    variables = kwargs.get('variables') or {}
    in_memory = kwargs.get('in_memory', False)
    file_format = kwargs.get('file_format', False)
    append = kwargs.get('append', False)
    variables['object_list'] = kwargs['object_list']
    variables['append'] = append
    if file_format in ('xlsx', 'xls'):
        variables['mark_unsafe'] = True
    data = render_to_string(template, variables)
    data = data.rstrip('\n')
    if file_format == 'xlsx':
        wb = Workbook()
        ws = wb.new_sheet("Export")
        ws_row = 1
        for line in data.split('\n'):
            for i, data in enumerate(_process_line(line), start=1):
                ws.set_cell_value(ws_row, i, data)
            ws_row += 1
        if in_memory:
            f = tempfile.NamedTemporaryFile(delete=False)
            file_name = f.name
            f.close()
        wb.save(file_name)
        if in_memory:
            return open(file_name, 'rb').read()
    elif file_format == 'xls':
        wb = WorkbookOld()
        ws = wb.add_sheet('0')
        for r, line in enumerate(data.split('\n'), start=1):
            for c, l in enumerate(_process_line(line)):
                ws.write(r, c, l)
        if in_memory:
            f = tempfile.NamedTemporaryFile(delete=False)
            file_name = f.name
            f.close()
        wb.save(file_name)
        if in_memory:
            return open(file_name, 'rb').read()
    else:
        if in_memory:
            return smart_bytes(data, encoding, errors='replace')
        else:
            if append:
                out = io.open(file_name, 'a', encoding=encoding)
                out.write('\n')
            else:
                out = io.open(file_name, 'w', encoding=encoding)
            out.write(data)
            out.close()

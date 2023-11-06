import io
import sys

def _find_first(haystack, needles, start=0):
    result = -1
    result_str = None
    for needle in needles:
        index = haystack.find(needle, start)
        if index != -1 and (result == -1 or index < result):
            result = index
            result_str = needle
    return result_str, result

def _update_location(string, line, col):
    lines = string.count('\n')
    if lines:
        line += lines
        col = len(string.rsplit('\n', 1)[1])
    else:
        col += len(string)
    return line, col

class TemplatingState:
    outfile = None

    def __init__(self, outfile=None):
        self.outfile = outfile or sys.stdout
        self.variables = {}

        self.variables['lt'] = '<'
        self.variables['gt'] = '>'
        self.variables['lb'] = '{'
        self.variables['rb'] = '}'

    def report_error(self, full_source, filename, line, column, message):
        print(f"Error: {message}")
        print(f"in file {filename}, line {line}, column {column}:")
        print(full_source.splitlines()[line-1])
        print(' '*(column - 1) + '^')
        sys.exit(1)

    def process_filename(self, filename):
        with open(filename, 'r') as f:
            self.process(f.read(), filename=filename)

    def process(self, source, filename='', line=1, col=1, full_source=None):
        index = 0
        if full_source is None:
            full_source = source

        while True:
            next_directive, next_index = _find_first(source, ('<%', '{{'), index)
            if next_directive is None:
                self.outfile.write(source[index:])
                return
            self.outfile.write(source[index:next_index])
            line, col = _update_location(source[index:next_index], line, col)
            if next_directive == '{{':
                end_index = source.find('}}', next_index)
                if end_index == -1:
                    self.report_error(full_source, filename, line, col, "'{{' without matching '}}'")
                varname = source[next_index+2:end_index]
                if '{{' in varname:
                    self.report_error(full_source, filename, line, col, "variable name may not contain '{{'")
                if varname not in self.variables:
                    self.report_error(full_source, filename, line, col, f"undefined variable: {varname}")
                self.outfile.write(self.variables[varname])
                line, col = _update_location(source[next_index:end_index+2], line, col)
                index = end_index+2
            elif next_directive == '<%':
                varname_end = source.find('>', next_index)
                if varname_end == -1:
                    self.report_error(full_source, filename, line, col, "'<%' without matching '>'")
                varname = source[next_index+2:varname_end]
                if '{{' in varname:
                    self.report_error(full_source, filename, line, col, "variable name may not contain '{{'")

                #not sure why anyone would nest variable declarations, but just in case
                nest_count = 1
                close_index = next_index
                open_tag = f'<%{varname}>'
                close_tag = f'</%{varname}>'
                while nest_count > 0:
                    found_tag, close_index = _find_first(source, (open_tag, close_tag), close_index + 1)
                    if found_tag == open_tag:
                        nest_count += 1
                    elif found_tag == close_tag:
                        nest_count -= 1
                    else:
                        self.report_error(full_source, filename, line, col, "'<%{varname}>' without matching '</%{varname}>'")

                #advance line, col to the start of the variable contents so we can pass them in directly
                line, col = _update_location(source[next_index:varname_end+1], line, col)

                varstream = io.StringIO()
                prev_outfile = self.outfile
                self.outfile = varstream
                self.process(source[varname_end+1:close_index], filename, line, col, full_source)
                self.outfile = prev_outfile

                self.variables[varname] = varstream.getvalue()

                index = close_index + len(close_tag)
                line, col = _update_location(source[varname_end+1:index], line, col)

def main():
    st = TemplatingState()
    for filename in sys.argv[1:]:
        st.process_filename(filename)

if __name__ == '__main__':
    sys.exit(main())

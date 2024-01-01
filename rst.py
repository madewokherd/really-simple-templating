import io
import sys

def _find_first(haystack, needles, start=0):
    result = -1
    result_str = None
    for needle in needles:
        index = haystack.find(needle, start)
        if index != -1 and (result == -1 or index < result):
            result = index
            result_str = haystack[index:index+len(needle)] # preserves source location
    return result_str, result

class StringLocation(str):
    __slots__ = ['line', 'column', 'filename', 'file_contents']

    def __new__(cls, s, filename, line=1, column=1, file_contents=None):
        self = str.__new__(cls, s)
        self.filename = filename
        self.line = line
        self.column = column
        if file_contents is None:
            self.file_contents = s
        else:
            self.file_contents = file_contents
        return self

    def __getitem__(self, index):
        s = super().__getitem__(index)
        if isinstance(index, slice):
            index = index.start
        prefix = super().__getitem__(slice(0, index))
        lines = prefix.count('\n')
        if lines:
            line = self.line + lines
            col = len(prefix.rsplit('\n', 1)[1])+1
        else:
            line = self.line
            col = self.column + len(prefix)
        return StringLocation(s, self.filename, line, col, self.file_contents)

class TemplatingState:
    outfile = None

    def __init__(self, outfile=None):
        self.outfile = outfile or sys.stdout
        self.variables = {}

        self.variables['lt'] = '<'
        self.variables['gt'] = '>'
        self.variables['lb'] = '{'
        self.variables['rb'] = '}'

    def report_error(self, source_string, message):
        print(f"Error: {message}")
        if isinstance(source_string, StringLocation):
            print(f"in file {source_string.filename}, line {source_string.line}, column {source_string.column}:")
            print(source_string.file_contents.splitlines()[source_string.line-1])
            print(' '*(source_string.column - 1) + '^')
        else:
            print(f"in string: {source_string}")
        sys.exit(1)

    def process_filename(self, filename):
        with open(filename, 'r') as f:
            self.process(StringLocation(f.read(), filename))

    def process(self, source):
        index = 0

        while True:
            next_directive, next_index = _find_first(source, ('<%', '{{'), index)
            if next_directive is None:
                self.outfile.write(source[index:])
                return
            self.outfile.write(source[index:next_index])
            if next_directive == '{{':
                end_index = source.find('}}', next_index)
                if end_index == -1:
                    self.report_error(next_directive, "'{{' without matching '}}'")
                varname = source[next_index+2:end_index]
                if '{{' in varname:
                    self.report_error(varname[varname.index('{{')], "variable name may not contain '{{'")
                if varname not in self.variables:
                    self.report_error(varname, f"undefined variable: {varname}")
                self.outfile.write(self.variables[varname])
                index = end_index+2
            elif next_directive == '<%':
                varname_end = source.find('>', next_index)
                if varname_end == -1:
                    self.report_error(next_directive, "'<%' without matching '>'")
                varname = source[next_index+2:varname_end]
                if '{{' in varname:
                    self.report_error(varname[varname.index('{{')], "variable name may not contain '{{'")

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
                        self.report_error(next_directive, f"'<%{varname}>' without matching '</%{varname}>'")

                varstream = io.StringIO()
                prev_outfile = self.outfile
                self.outfile = varstream
                self.process(source[varname_end+1:close_index])
                self.outfile = prev_outfile

                self.variables[varname] = varstream.getvalue()

                index = close_index + len(close_tag)

def main():
    st = TemplatingState()
    for filename in sys.argv[1:]:
        st.process_filename(filename)

if __name__ == '__main__':
    sys.exit(main())

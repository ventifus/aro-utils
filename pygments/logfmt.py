from pygments.lexer import RegexLexer, default, include
from pygments.token import Text, Number, Keyword, Generic, Comment, Literal, Operator, String

class CustomLexer(RegexLexer):
    """
    For logfmt log lines.
    """
    name = 'Logfmt'
    aliases = 'logfmt'
    filenames = '*.log'

    tokens = {
        'root': [
            # (r'^ERRO', Generic.Error),
            # (r'^WARN', Generic.Strong),
            # (r'^INFO', Text),
            # (r'^DEBU', Comment),
            # (r'^TRAC', Generic.Comment),
            (r'\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z]', Comment),
            (r'=', Operator),
            (r'\w+(?==)', Keyword),
            (r'(?==)\w+', Literal),
        ],    
        'base': [
            (r'\[[0-9. ]+\] ', Number),
            (r'(?<=\] ).+?:', Keyword),
            (r'\n', Text, '#pop'),
        ],
    }
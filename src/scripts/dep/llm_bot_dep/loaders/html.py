import re

def process_html(htmlstr: str):
    logger.info("Processing HTML file...")
    # filter out DOCTYPE
    htmlstr = ' '.join(htmlstr.split())
    re_doctype = re.compile(r'<!DOCTYPE .*?>', re.S)
    s = re_doctype.sub('', htmlstr)
    
    # filter out CDATA
    re_cdata = re.compile('//<!\[CDATA\[[^>]*//\]\]>', re.I)
    s = re_cdata.sub('', s)
    
    # filter out Script
    re_script = re.compile('<\s*script[^>]*>[^<]*<\s*/\s*script\s*>', re.I)
    s = re_script.sub('', s)
    
    # filter out style
    re_style = re.compile('<\s*style[^>]*>[^<]*<\s*/\s*style\s*>', re.I)
    s = re_style.sub('', s)
    
    # transfor br to \n
    re_br = re.compile('<br\s*?/?>')
    s = re_br.sub('', s)
    
    # filter out HTML tags
    re_h = re.compile('<\?[\w+[^>]*>')
    s = re_h.sub('', s)
    
    # filter out HTML comments
    re_comment = re.compile('<!--[^>]*-->')
    s = re_comment.sub('', s)
    
    # remove extra blank lines
    blank_line = re.compile('\n+')
    s = blank_line.sub('', s)
    
    # remove hyperlinks
    http_link = re.compile(r'(http://.+html)')
    s = http_link.sub('', s)
    
    return s

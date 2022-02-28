from datetime import date


months_de = ['Jan.', 'Feb.', 'Mär.', 'Apr.', 'Mai', 'Jun.',
             'Jul.', 'Aug.', 'Sep.', 'Okt.', 'Nov.', 'Dez.']


months_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def ordinal(n: int) -> str:
    """
    from: https://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd#answer-4712
    """
    result = "%d%s" % (n, "tsnrhtdd"[((n / 10 % 10 != 1) * (n % 10 < 4) * n % 10)::4])
    return result.replace('11st', '11th').replace('12nd', '12th').replace('13rd', '13th')


def human_date(dt: date, language='en') -> str:
    if language == 'en':
        return dt.strftime('%B {} %Y').format(ordinal(dt.day))
    elif language == 'de':
        return chr(160).join(
            (str(dt.day) + '.', months_de[dt.month-1], str(dt.year)))
    elif language == 'es':
        return (chr(160) + 'de' + chr(160)).join(
            (str(dt.day), months_es[dt.month-1], str(dt.year)))
    else:  # Fall-back
        return dt.strftime('%Y-%m-%d')

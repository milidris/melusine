import re
from melusine.config.config import ConfigJsonReader
from melusine.prepare_email.cleaning import remove_accents

conf_reader = ConfigJsonReader()
config = conf_reader.get_config_file()
REGEX_TR_RE = config['regex']['manage_transfer_reply']
REGEX_SEG = config['regex']['mail_segmenting']

regex_begin_transfer = REGEX_TR_RE['begin_transfer']
regex_transfer_other = REGEX_TR_RE['transfer_other']
regex_extract_from = REGEX_TR_RE['extract_from']
regex_extract_to = REGEX_TR_RE['extract_to']
regex_extract_date = REGEX_TR_RE['extract_date']
regex_extract_header = REGEX_TR_RE['extract_header']
regex_answer_header = REGEX_TR_RE['answer_header']
regex_transfert_header = REGEX_TR_RE['transfer_header']

regex_segmenting_dict = REGEX_SEG['segmenting_dict']
regex_segmenting_dict['RE/TR'] = [regex_begin_transfer,
                                  regex_transfer_other,
                                  regex_extract_from,
                                  regex_extract_to,
                                  regex_extract_date,
                                  regex_extract_header,
                                  regex_answer_header,
                                  regex_transfert_header]

regex_from1 = REGEX_SEG['meta_from1']
regex_from2 = REGEX_SEG['meta_from2']
regex_to = REGEX_SEG['meta_to']
regex_date1 = REGEX_SEG['meta_date1']
regex_date2 = REGEX_SEG['meta_date2']
regex_header = REGEX_SEG['meta_header']
regex_piece_jointe = REGEX_SEG['pattern_pj']

regex_exception_une_lettre_maj = REGEX_SEG['pattern_exception_une_lettre_maj']
regex_exception_Mr = REGEX_SEG['pattern_exception_Mr']
regex_exception_Dr = REGEX_SEG['pattern_exception_Dr']
regex_exception_Mme = REGEX_SEG['pattern_exception_Mme']
regex_exception = REGEX_SEG['pattern_exception']
regex_pattern_exceptions = (regex_exception_une_lettre_maj
                            + regex_exception_Mr
                            + regex_exception_Dr
                            + regex_exception_Mme
                            + regex_exception)

regex_sep_doubles_points_virgules_espace = REGEX_SEG['pattern_sep_doubles_points_virgules_espace']
regex_pattern_separteurs_evidents = REGEX_SEG['pattern_separteurs_evidents']
regex_pattern_beginning = REGEX_SEG['pattern_beginning']
regex_pattern_end = REGEX_SEG['pattern_end']
regex_pattern = (regex_pattern_beginning
                 + regex_pattern_separteurs_evidents
                 + regex_sep_doubles_points_virgules_espace
                 + regex_pattern_exceptions
                 + regex_pattern_end)

regex_typo = REGEX_SEG['tag_typo']
regex_tag = REGEX_SEG['tag']
regex_tag_subsentence = REGEX_SEG['tag_subsentence']
regex_split_message_to_sentences_list = REGEX_SEG['split_message_to_sentences_list']


def structure_email(row):
    """ 1. Splits parts of each messages in historic and tags them.
    For example a tag can be hello, body, greetings etc
    2. Extracts the meta informations of each messages

    To be used with methods such as: `apply(func, axis=1)` or
    `apply_by_multiprocessing(func, axis=1, **kwargs)`.

    Parameters
    ----------
    row : row of pd.Dataframe, apply on column ['structured_historic']

    Returns
    -------
    list of dicts : one dict per message

    Examples
    --------
        >>> import pandas as pd
        >>> from melusine.prepare_email.build_historic import build_historic
        >>> data = pd.read_pickle('./tutorial/data/emails_anonymized.pickle')
        >>> data['structured_historic'] = data.apply(build_historic, axis=1)
        >>> # data contains column ['structured_historic']

        >>> from melusine.prepare_email.mail_segmenting import structure_email
        >>> structure_email(data.iloc[0])  # apply for 1 sample
        >>> data.apply(structure_email, axis=1)  # apply to all samples

    """
    structured_body = []
    for message in row['structured_historic']:
        structured_message = structure_message(message)
        if len(structured_message["structured_text"]["text"]) == 0:
            if structured_message["structured_text"]["header"] is None:
                continue
        structured_body.append(structured_message)

    return structured_body


def structure_message(message):
    """ Splits parts of a message and tags them.
    For example a tag can be hello, body, greetings etc
    Extracts the meta informations of the message

    Parameters
    ----------
    message : dict

    Returns
    -------
    dict

    Examples
    --------
    """
    meta = str(message.get("meta"))
    structured_meta, header = structure_meta(meta)
    text = str(message.get("text"))
    tagged_parts_list = tag_parts_message(text)
    structured_message = _tuples_to_dict(structured_meta,
                                         header,
                                         tagged_parts_list)

    return structured_message


def structure_meta(meta):
    """ Extract meta informations (date, from, to, header) from string meta

    Parameters
    ----------
    meta : str

    Returns
    -------
    tuple(dict, string)

    Examples
    --------
    """
    structured_meta = {}
    structured_meta['date'] = _find_date(meta)
    structured_meta['from'] = _find_from(meta)
    structured_meta['to'] = _find_meta(regex_to, meta)
    header = _find_meta(regex_header, meta)

    return structured_meta, header


def _find_date(message):
    """ Match pattern regex with a given message """
    group = _find_meta(regex_date1, message)
    if group is None:
        group = _find_meta(regex_date2, message)

    return group


def _find_from(message):
    """ Match pattern regex with a given message """
    group = _find_meta(regex_from1, message)
    if group is None:
        group = _find_meta(regex_from2, message)

    return group


def _find_meta(regex, message):
    """ Match pattern regex with a given message """
    groups = re.findall(regex, message)
    if len(groups) < 1:
        return None
    else:
        return groups[0]


def tag_parts_message(text):
    """ Splits message into sentences, tags them and merges two sentences in a
    row having the same tag.

    Parameters
    ----------
    text : str,


    Returns
    -------
    list of tuples

    Examples
    --------
    """
    sentence_list = split_message_to_sentences(text)
    tagged_sentence_list = []
    for sentence in sentence_list:
        tagged_sentence = tag_sentence(sentence)
        tagged_sentence_list.extend(tagged_sentence)
    tagged_parts_list = _merge_parts(tagged_sentence_list)
    tagged_parts_list = _remove_empty_parts(tagged_parts_list)
    tagged_parts_list = _update_typo_parts(tagged_parts_list)
    tagged_parts_list = _remove_typo_parts(tagged_parts_list)

    return tagged_parts_list


def split_message_to_sentences(text, sep_=r"(.*?[;.,?!])"):
    """ Split each sentences in a text """
    regex1 = regex_split_message_to_sentences_list[0]
    regex2 = regex_split_message_to_sentences_list[1]
    regex3 = regex_split_message_to_sentences_list[2]
    regex4 = regex_split_message_to_sentences_list[3]
    text = text.strip(regex1).lstrip(regex2)
    text = re.sub(regex3, regex4, text)      # remove double punctuation
    sentence_list = re.findall(regex_pattern, text, flags=re.M)
    sentence_list = [r for s in sentence_list
                     for r in re.split(regex_piece_jointe, s) if r]

    return sentence_list


def tag_sentence(sentence, default='BODY'):
    """ Tag a sentence.
    If the sentence cannot be tagged it will tag the subsentences

    Parameters
    ----------
    sentence : str,


    Returns
    -------
    list of tuples : sentence, tag

    Examples
    --------
    """
    tagged_sentence, tagged = tag(sentence)
    if tagged:
        return tagged_sentence
    else:
        return _tag_subsentence(sentence)


def _tag_subsentence(sentence, default='BODY'):
    """ Tags the subsentences in a sentence.
    If the subsentences cannot be tagged it will return the whole sentence with
    a default tag.

    Parameters
    ----------
    sentence : str,


    Returns
    -------
    list of tuples : sentence, tag

    Examples
    --------
    """
    subsentence_list = re.findall(regex_tag_subsentence, sentence, flags=re.M)
    tagged_subsentence_list = []
    any_sub_catch = False
    for subsentence in subsentence_list:
        tagged_subsentence, subcatch = tag(subsentence)
        if subcatch:
            tagged_subsentence_list.extend(tagged_subsentence)
            any_sub_catch = True
        else:
            tagged_subsentence_list.append((subsentence, default))
    if any_sub_catch:
        return tagged_subsentence_list
    else:
        return [(sentence, default)]


def tag(string):
    """ Tags a string.

    Parameters
    ----------
    string : str,


    Returns
    -------
    tuples : list of tuples and boolean

    Examples
    --------
    """
    regex_parts = regex_segmenting_dict.items()
    sentence_with_no_accent = remove_accents(string)
    for k, reg in regex_parts:
        for r in reg:
            r = r.replace(" ", regex_tag)
            if re.search(r, sentence_with_no_accent, re.I):
                return [(string, k)], True

    return string, False


def _merge_parts(list_de_tuple_parts_id):
    """ Merge two consecutives strings with the same tag """
    if len(list_de_tuple_parts_id) <= 1:
        return list_de_tuple_parts_id
    i = 0
    j = 1
    sentences, tags = zip(*list_de_tuple_parts_id)
    tags = list(tags)
    sentences = list(sentences)
    while j < len(list_de_tuple_parts_id):
        if tags[i] == tags[j]:
            sentences[i] = " ".join((sentences[i], sentences[j]))
            j += 1
        else:
            i += 1
            tags[i] = tags[j]
            sentences[i] = sentences[j]
            j += 1
    list_de_tuples_merged = list(zip(sentences[:i+1], tags[:i+1]))

    return list_de_tuples_merged


def _remove_empty_parts(tagged_parts_list):
    """ Remove all the empty parts in the list of tagged parts """
    tagged_parts_list = [part for part in tagged_parts_list
                         if len(part[0]) > 0]

    return tagged_parts_list


def _update_typo_parts(tagged_parts_list):
    """ Update the tagging for all the typo parts in the list of
    tagged parts """
    tagged_parts_list = [_update_typo_part(part_tag_tuple)
                         for part_tag_tuple in tagged_parts_list]

    return tagged_parts_list


def _update_typo_part(part_tag_tuple):
    part, tag = part_tag_tuple
    if __is_typo(part):
        part_tag_tuple = part, "TYPO"

    return part_tag_tuple


def __is_typo(part, regex_typo=regex_typo):
    """ Check if a string is typo """
    return re.search(regex_typo, part, re.I & re.M)


def _remove_typo_parts(tagged_parts_list):
    """  """
    tagged_parts_list = [part_tag_tuple
                         for part_tag_tuple in tagged_parts_list
                         if part_tag_tuple[1] != "TYPO"]

    return tagged_parts_list


def _tuples_to_dict(meta, header, tagged_parts):
    """ Convert a dictionnary and list of tuples into dictionnary """
    structured_message = {}
    structured_message["meta"] = meta
    structured_message["structured_text"] = {}
    structured_message["structured_text"]["header"] = header
    structured_text = []
    for part, tag in tagged_parts:
        dict_message = {}
        dict_message["part"] = part
        dict_message["tags"] = tag
        structured_text.append(dict_message)
    structured_message["structured_text"]["text"] = structured_text

    return structured_message

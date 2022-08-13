import re,logging

def get_key_value_by_colon_or_equal_sign(str_buffer): # and not remove SPACE in key and value.
    key = None
    value = None
    temp_hash = {}
    
    lines = re.split(r'[\r\n]+',str_buffer)

    for line in lines :
        #logging.debug('[%s]' %line)
        if line[:3] == '###':
            continue
        if not re.search(r'\w', line):
            continue

        key     = None
        value   = None
        matches = re.match(r'^\s*(\S[^=:]*[^:=\s])\s*[:=]\s*(.*?)\s*$',line, re.DOTALL)

        if matches:
            key     = matches.group(1)
            value   = matches.group(2)
            #logging.debug('KEY [%s] VALUE [%s]' %(key,value))
        else:
            matches = re.search(r'^\s*(\S+)\s*[:=]|^\s*(\S*.*\S)\s*$', line)
            if matches:
                key     = matches.group(1) or matches.group(2)
                value   = "KEY_WITHOUT_VALUE"
                #logging.debug('KEY [%s] VALUE [%s]' %(key,value))
            else:
                raise Exception('impossible' , line)

        generated_key = key
        for iii in range(1,99):
            try:
                temp_hash[generated_key]
                generated_key = '%s_%d' %(key,iii)
            except:
                break
        temp_hash[generated_key] = value

    #print temp_hash
    return temp_hash

def cmp_template_block(template, msg_blk) :
    template_hash = get_key_value_by_colon_or_equal_sign(template)
    msg_blk_hash  = get_key_value_by_colon_or_equal_sign(msg_blk)
    mis_matched = 0;
    itme_check  = 0;

    for tempalte_key in template_hash.keys():
        itme_check = itme_check + 1

        try:
            msg_blk_hash[tempalte_key]
        except:
            logging.info("missing %s = [%s]"%(tempalte_key,template_hash[tempalte_key]))
            mis_matched = mis_matched + 1
            continue

        if msg_blk_hash[tempalte_key] == template_hash[tempalte_key]:
            logging.debug ("   OK. %35s = [%s]"%(tempalte_key,template_hash[tempalte_key]))
            continue

        if template_hash[tempalte_key][:3] == '###':
            logging.debug("   OK. %35s = [%s] [%s]"%(tempalte_key,template_hash[tempalte_key], msg_blk_hash[tempalte_key]))
            continue

        if re.match(template_hash[tempalte_key],r'#'):
            len_value = len(msg_blk_hash[tempalte_key])
            if msg_blk_hash[tempalte_key] == template_hash[tempalte_key][:len_value]:
                continue

        logging.info("FAIL. %35s = [%s] [%s]"%(tempalte_key,template_hash[tempalte_key], msg_blk_hash[tempalte_key]))
        mis_matched = mis_matched + 1

    if mis_matched:
        logging.debug(msg_blk)
        logging.info("item_checked %d, mis_matched %d."%(itme_check,mis_matched))
        return True

    logging.debug("item_checked %d, ALL matched."%(itme_check))
    return False

def get_block_from_data_buffer(str_buffer, separator = "\[.*\]"):
    block_dict = dict()
    temp_key = None
    temp_buff = ""
    lines = re.split(r'[\r\n]+', str_buffer)
    for line in lines:
        if re.match(r'%s'%(separator),line):
            if temp_key != None and len(temp_buff):
                print (temp_buff)
                block_dict[temp_key] = get_key_value_by_colon_or_equal_sign(temp_buff)
            block_dict[line] = dict()
            temp_key = line
            continue

        if temp_key != None:
            temp_buff = temp_buff + line + "\r\n"

    return block_dict

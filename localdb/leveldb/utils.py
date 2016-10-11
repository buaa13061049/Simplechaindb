"""Utils to initialize and drop the localdb [levelDB]."""
# bytes can only contain ASCII literal characters.

import plyvel as l
import rethinkdb as r
import bigchaindb
import rapidjson

import os
import logging

logger = logging.getLogger(__name__)

# path should be exist
config = {
    'database': {
        'path': '/localdb/',
        'tables':['header','bigchain','votes']
    },
    'encoding':'utf-8'
}

#singleton localdb pool
class LocalDBPool(object):
    # tips: first should release the leveldb dir block
    parent_dir = config['database']['path']
    # if parent_dir and not os.path.exists(parent_dir):
    #     os.makedirs(parent_dir)

    for table in config['database']['tables']:
        try:
            lock_path = parent_dir + table + "//LOCK"
            logger.warn('remove leveldb LOCK ' + str(lock_path))
            if(os.path.exists(lock_path)):
                os.remove(lock_path)
        except Exception as ex:
            # logger.warn(str(ex))
            continue

    conn = dict()
    conn['header'] = l.DB(parent_dir+'header/',create_if_missing=True)
    conn['bigchain'] = l.DB(parent_dir+'bigchain/',create_if_missing=True)
    conn['votes'] = l.DB(parent_dir+'votes/',create_if_missing=True)

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(LocalDBPool, cls).__new__(cls)
            logger.info('init localpool ...')
        return cls.instance

def init():
    """ init leveldb database by conn"""
    logger.info('leveldb init...')
    conn_bigchain = get_conn('bigchain')
    conn_header = get_conn('header')

    logger.info('leveldb init...')
    logger.info('leveldb/header init...')
    logger.info('leveldb/header init host...' + str(bigchaindb.config['database']['host']))
    logger.info('leveldb/header init public_key...' + str(bigchaindb.config['keypair']['public']))
    logger.info('leveldb/header init private_key...' + str(bigchaindb.config['keypair']['private']))

    update(conn_header, 'host', bigchaindb.config['database']['host'])
    update(conn_header, 'public_key', bigchaindb.config['keypair']['public'])
    update(conn_header, 'private_key', bigchaindb.config['keypair']['private'])

    block_num = int(get_withdefault(conn_header, 'block_num', 0))
    genesis_block_id = get_withdefault(conn_header,'genesis_block_id','0')
    if block_num == 0 :
        genesis_block = r.db('bigchain').table('bigchain').order_by(r.asc(r.row['block']['timestamp'])).limit(1).run(
            bigchaindb.Bigchain().conn)[0]
        genesis_block_id = genesis_block['id']
        genesis_block_json_str = rapidjson.dumps(genesis_block)
        insert(conn_bigchain, genesis_block_id, genesis_block_json_str)
        insert(conn_header, 'genesis_block_id', genesis_block_id)
        insert(conn_header, 'block_num', 1)
        insert(conn_header, 'current_block_id', genesis_block_id)
    logger.info('leveldb/header genesis_block_id...' + str(genesis_block_id))
    logger.info('leveldb init done')


def close(conn):
    """ close conn """
    if conn:
        l.close(conn)
        logger.info('leveldb close conn ... ' + str(conn))


def close_all():
    """ close all databases dir """
    tables = config['database']['tables']
    logger.info('leveldb close all databases '+str(tables))
    result=[]
    for table in tables:
        if table is not None:
            try:
                dir = config['database']['path']+table+'/'
                l.close(dir)
                result.append(dir)
            except:
                # print(table + ' is not exist')
                continue
    logger.info('leveldb close all...' + str(result))


def get_conn(name):
    """ get the leveldb """
    return LocalDBPool.conn[name]


def insert(conn,key,value):
    # logger.info('leveldb insert...' + str(key) + ":" +str(value))
    conn.put(bytes(str(key),config['encoding']),bytes(str(value),config['encoding']))


def batch_insert(conn,dict):
    with conn.write_batch() as b:
        for key in dict:
            # logger.warn('key: ' + str(key) + ' --- value: ' + str(dict[key]))
            b.put(bytes(str(key),config['encoding']),bytes(str(dict[key]),config['encoding']))


def delete(conn,key):
    # logger.info('leveldb delete...' + str(key) )
    conn.delete(bytes(str(key),config['encoding']))


def batch_delete(conn,dict):
    with conn.write_batch() as b:
        for key,value in dict:
            b.delete(bytes(str(key),config['encoding']))


def update(conn,key,value):
    # logger.info('leveldb update...' + str(key) + ":" +str(value))
    conn.put(bytes(str(key),config['encoding']), bytes(str(value),config['encoding']))


def get(conn,key):
    # logger.info('leveldb get...' + str(key))
    # get the value for the bytes_key,if not exists return None
    # bytes_val = conn.get_property(bytes(key, config['encoding']))
    bytes_val = conn.get(bytes(str(key), config['encoding']))
    return bytes(bytes_val).decode(config['encoding'])


def get_prefix(conn,prefix):
    """
        block-v1=v1
        block-v2=v2
        block-v3=v3
        prefix = 'block'  => {'-v1':'v1','-v2':'v2','-v3':'v3'}
        prefix = 'block-' => {'v1':'v1','v2':'v2','v3':'v3'}
        """
    logger.warn(str(conn) + ' , ' + str(prefix))
    if conn:
        bytes_dict_items = conn.prefixed_db(bytes(str(prefix),config['encoding']))
        result = {}
        for key,value in bytes_dict_items:
            key = bytes(key).decode(config['encoding'])
            value = bytes(value).decode(config['encoding'])
            result[key] = value
        return result
    else:
        return None


def get_withdefault(conn,key,default_value):
    # logger.info('leveldb get...' + str(key) + ",default_value=" + str(default_value))
    # get the value for the bytes_key,if not exists return defaule_value
    bytes_val = conn.get(bytes(str(key),config['encoding']),bytes(str(default_value),config['encoding']))
    # return bytes(bytes_val).decode(config['encoding'])
    # logger.info('leveldb get...' + str(key) + ",default_value=" + bytes(bytes_val).decode(config['encoding']))
    return bytes(bytes_val).decode(config['encoding'])

# qinhuawei@outlook.com

from comm.ssh_engine import ssh_connect, go_thread
import logging,re,types,threading,time
from comm.msg_compare import *

class manage_connections():

    def test_linux_prompt(self, connection, chan_name):
        if not chan_name.startswith('linux'):
            return
        channel = connection.chan_dict[chan_name]
        try:
            prompt = connection.config['shells']['linux']
            if prompt:
                channel.exec_command('true', prompt=prompt, timeout=60)
            else:
                raise True
        except KeyError:
            channel.guess_prompt()

    def create_conn_chan(self, conn_name, chan_name, close_and_open=False):
        if (not chan_name.startswith('linux')) and (not chan_name.startswith('router')):
            raise Exception('CHAN_NAME', 'create chan -> conn_name %s, chan_name %s, invalid channel name' %(conn_name, chan_name))

        connection = self.conn_dict[conn_name]
        chan_type=chan_name.split('_')[0]
        prompt = connection.config['shells'][chan_type]

        if self.log_on_screen > 0:
            log_on_screen = True
        else:
            try:
                log_on_screen = connection.config['log_on_screen']
            except:
                log_on_screen = False

        try:
            if close_and_open:
                connection.close_shell(chan_name)
                logging.debug('create chan -> conn_name %s, chan_name %s close_and_open=True' %(conn_name, chan_name))
        except:
            pass
        try:
            return connection.chan_dict[chan_name]
        except:
            pass
        logging.debug('create chan -> conn_name %s, chan_name %s, prompt [%s]' %(conn_name, chan_name, prompt))
        channel = connection.invoke_shell(chan_name, log_on_screen=log_on_screen)

        if chan_name.startswith('linux'):
            self.test_linux_prompt(connection, chan_name)

        return channel

    def create_conn(self, conn_name, close_and_open=False):
        try:
            if close_and_open:
                self.close_connection(conn_name)
            else:
                return self.conn_dict[conn_name]
        except:
            pass

        host = self.conn_cfg[conn_name]
        try:
            jumer_list = host['jumper']
        except:
            jumer_list = []
        proxy_list = []
        for proxy in jumer_list:
            if proxy.__class__ != dict:
                proxy_list.append(self.conn_cfg[proxy])
            else:
                proxy_list.append(proxy)

        logging.debug('create connection -> host %s, conn_name %s' %(host['host'], conn_name))
        try:
            connection = ssh_connect(host['host'],host['user'],passwd=host['passwd'],port=host['port'],alias=conn_name,log_folder=self.log_folder, proxy_list=proxy_list)
        except:
            logging.exception('----------conn_name [%s] %s ------------' %(conn_name,str(host)))
            connection = ssh_connect(host['host'],host['user'],port=host['port'],key_filename=host['pkey'],alias=conn_name,log_folder=self.log_folder, proxy_list=proxy_list)
        setattr(self, conn_name, connection)
        self.conn_dict[conn_name] = connection
        connection.config = self.conn_cfg[conn_name]

        return connection

    def create_connections(self,):
        logging.debug(self.required_connections)
        for conn_name, chan_list in self.required_connections.items(): # self.required_connections.iteritems():
            self.create_conn(conn_name)
            for chan_name in chan_list:
                def thread_create_conn_chan(conn_name, chan_name):
                    try:
                        self.create_conn_chan(conn_name, chan_name)
                    except Exception:
                        logging.exception   ('========= invoke %s %s failed =======' %(conn_name, chan_name))
                        self.case_result = 'INVOKE %s %s' %(conn_name, chan_name)
                        return
                go_thread(thread_create_conn_chan, args=(conn_name, chan_name))

        go_thread.join_threads()
        if self.case_result:
            raise Exception(self.case_result,'')

    def close_connection(self, conn_name):
        try:
            delattr(self, conn_name)
        except:
            pass
        try:
            connection = self.conn_dict.pop(conn_name)
            connection.close()
        except:
            pass

    def close_all_connections(self,):
        conn_list = list(self.conn_dict.keys())
        for conn_name in conn_list:
            self.close_connection(conn_name)

def create_connections(conn_dict):
    def real_decorator(function):
        def wrapper(*args, **kwargs):
            self = args[0]
            self.required_connections = conn_dict
            self.create_connections()
            return function(*args, **kwargs)
        return wrapper
    return real_decorator
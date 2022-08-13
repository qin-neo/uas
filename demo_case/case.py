# qinhuawei@outlook.com
import logging,sys,os,subprocess,re,time
from comm.case_templates import case_template_00
from comm.ssh_engine import go_thread
from comm.ssh_connections import create_connections

class uas_case(case_template_00):
    required_connections = {
        'centos'    : ['linux',],
    }

    # python uas.py -r demo_case -e run_hostname
    @create_connections(required_connections)
    def run_hostname(self,):
        self.centos.linux.exec_command('hostname')

    # python uas.py -r demo_case
    def case_steps(self,):
        recv_buff = self.centos.linux.exec_command('ls /root/neoq')
        if not 'test_file' in recv_buff:
            raise Exception('FILE_NO_FOUND', recv_buff)

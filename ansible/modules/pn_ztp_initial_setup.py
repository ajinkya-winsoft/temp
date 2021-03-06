#!/usr/bin/python
""" PN Fabric Creation """
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import shlex
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pn_nvos import pn_cli

DOCUMENTATION = """
---
module: pn_ztp_initial_setup
author: 'Pluribus Networks (devops@pluribusnetworks.com)'
short_description: Module to perform fabric creation/join.
description:
    Zero Touch Provisioning (ZTP) allows you to provision new switches in your
    network automatically, without manual intervention.
    It performs following steps:
        - Disable STP
        - Enable all ports
        - Create/Join fabric
        - Enable STP
options:
    pn_fabric_name:
      description:
        - Specify name of the fabric.
      required: False
      type: str
    pn_fabric_network:
      description:
        - Specify fabric network type as either mgmt or in-band.
      required: False
      type: str
      choices: ['mgmt', 'in-band']
      default: 'mgmt'
    pn_fabric_control_network:
      description:
        - Specify fabric control network as either mgmt or in-band.
      required: False
      type: str
      choices: ['mgmt', 'in-band']
      default: 'mgmt'
    pn_toggle_port_speed:
      description:
        - Flag to indicate if 40g/100g ports should be converted to 10g/25g ports or not.
      required: False
      default: True
      type: bool
    pn_spine_list:
      description:
        - Specify list of Spine hosts
      required: False
      type: list
    pn_leaf_list:
      description:
        - Specify list of leaf hosts
      required: False
      type: list
    pn_inband_ipv4:
      description:
        - Inband ips to be assigned to switches starting with this value.
      required: False
      default: 192.168.0.1/24.
      type: str
    pn_inband_ipv6:
      description:
        - Inband ips to be assigned to switches starting with this value.
      required: False
      type: str
    pn_current_switch:
      description:
        - Name of the switch on which this task is currently getting executed.
      required: False
      type: str
    pn_static_setup:
      description:
        - Flag to indicate if static values should be assign to
        following switch setup params.
      required: False
      default: False
      type: bool
    pn_mgmt_ip:
      description:
        - Specify MGMT-IP value to be assign if pn_static_setup is True.
      required: False
      type: str
    pn_mgmt_ip_subnet:
      description:
        - Specify subnet mask for MGMT-IP value to be assign if
        pn_static_setup is True.
      required: False
      type: str
    pn_gateway_ip:
      description:
        - Specify GATEWAY-IP value to be assign if pn_static_setup is True.
      required: False
      type: str
    pn_dns_ip:
      description:
        - Specify DNS-IP value to be assign if pn_static_setup is True.
      required: False
      type: str
    pn_dns_secondary_ip:
      description:
        - Specify DNS-SECONDARY-IP value to be assign if pn_static_setup is True
      required: False
      type: str
    pn_domain_name:
      description:
        - Specify DOMAIN-NAME value to be assign if pn_static_setup is True.
      required: False
      type: str
    pn_ntp_server:
      description:
        - Specify NTP-SERVER value to be assign if pn_static_setup is True.
      required: False
      type: str
    pn_web_api:
      description:
        - Flag to enable web api.
      default: True
      type: bool
    pn_stp:
      description:
        - Flag to enable STP at the end.
      required: False
      default: True
      type: bool
    pn_autotrunk:
      description:
        - Flag to enable/disable auto-trunk setting.
      required: False
      choices: ['enable', 'disable']
      type: str
    pn_autoneg:
      description:
        - Flag to enable/disable auto-neg for T2+ platforms.
      required: False
      type: bool
"""

EXAMPLES = """
- name: Fabric creation/join
    pn_ztp_initial_setup:
      pn_fabric_name: 'ztp-fabric'
      pn_current_switch: "{{ inventory_hostname }}"
      pn_spine_list: "{{ groups['spine'] }}"
      pn_leaf_list: "{{ groups['leaf'] }}"
"""

RETURN = """
summary:
  description: It contains output of each configuration along with switch name.
  returned: always
  type: str
changed:
  description: Indicates whether the CLI caused changes on the target.
  returned: always
  type: bool
unreachable:
  description: Indicates whether switch was unreachable to connect.
  returned: always
  type: bool
failed:
  description: Indicates whether or not the execution failed on the target.
  returned: always
  type: bool
exception:
  description: Describes error/exception occurred while executing CLI command.
  returned: always
  type: str
task:
  description: Name of the task getting executed on switch.
  returned: always
  type: str
msg:
  description: Indicates whether configuration made was successful or failed.
  returned: always
  type: str
"""

CHANGED_FLAG = []


def run_cli(module, cli):
    """
    Method to execute the cli command on the target node(s) and returns the
    output.
    :param module: The Ansible module to fetch input parameters.
    :param cli: The complete cli string to be executed on the target node(s).
    :return: Output/Error or Success msg depending upon the response from cli.
    """
    results = []
    cli = shlex.split(cli)
    rc, out, err = module.run_command(cli)

    if out:
        return out
    if err:
        json_msg = {
            'switch': module.params['pn_current_switch'],
            'output': u'Operation Failed: {}'.format(' '.join(cli))
        }
        results.append(json_msg)
        module.exit_json(
            unreachable=False,
            failed=True,
            exception=err.strip(),
            summary=results,
            task='Fabric creation',
            msg='Fabric creation failed',
            changed=False
        )
    else:
        return 'Success'


def make_switch_setup_static(module):
    """
    Method to assign static values to different switch setup parameters.
    :param module: The Ansible module to fetch input parameters.
    """
    mgmt_ip = module.params['pn_mgmt_ip']
    mgmt_ip_subnet = module.params['pn_mgmt_ip_subnet']
    gateway_ip = module.params['pn_gateway_ip']
    dns_ip = module.params['pn_dns_ip']
    dns_secondary_ip = module.params['pn_dns_secondary_ip']
    domain_name = module.params['pn_domain_name']
    ntp_server = module.params['pn_ntp_server']
    cli = pn_cli(module)
    cli += ' switch-setup-modify '

    if mgmt_ip:
        ip = mgmt_ip + '/' + mgmt_ip_subnet
        cli += ' mgmt-ip ' + ip

    if gateway_ip:
        cli += ' gateway-ip ' + gateway_ip

    if dns_ip:
        cli += ' dns-ip ' + dns_ip

    if dns_secondary_ip:
        cli += ' dns-secondary-ip ' + dns_secondary_ip

    if domain_name:
        cli += ' domain-name ' + domain_name

    if ntp_server:
        cli += ' ntp-server ' + ntp_server

    clicopy = cli
    if clicopy.split('switch-setup-modify')[1] != ' ':
        run_cli(module, cli)


def update_switch_names(module, switch_name):
    """
    Method to update switch names.
    :param module: The Ansible module to fetch input parameters.
    :param switch_name: Name to assign to the switch.
    :return: String describing switch name got modified or not.
    """
    cli = pn_cli(module)
    cli += ' switch-setup-show format switch-name '
    if switch_name == run_cli(module, cli).split()[1]:
        return ' Switch name is same as hostname! '
    else:
        cli = pn_cli(module)
        cli += ' switch-setup-modify switch-name ' + switch_name
        run_cli(module, cli)
        return ' Updated switch name to match hostname! '


def modify_stp_local(module, modify_flag):
    """
    Method to enable/disable STP (Spanning Tree Protocol) on a switch.
    :param module: The Ansible module to fetch input parameters.
    :param modify_flag: Enable/disable flag to set.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    cli += ' switch-local stp-show format enable '
    current_state = run_cli(module, cli).split()

    if len(current_state) == 1:
        cli = pn_cli(module)
        cli += ' switch-local stp-modify ' + modify_flag
        return run_cli(module, cli)
    elif current_state[1] == 'yes':
        cli = pn_cli(module)
        cli += ' switch-local stp-modify ' + modify_flag
        return run_cli(module, cli)
    else:
        return ' Already modified '


def ports_modify_jumbo(module, modify_flag):
    """
    Method to enable/disable Jumbo flag on a switch ports.
    :param module: The Ansible module to fetch input parameters.
    :param modify_flag: Enable/disable flag to set.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    clicopy = cli
    trunk_ports = []
    cli += ' switch-local port-show format port,trunk status trunk no-show-headers'
    cli_out = run_cli(module, cli)
    if cli_out == 'Success':
        pass
    else:
        cli_out = cli_out.strip().split('\n')
        for output in cli_out:
            output = output.strip().split()
            port, trunk_name = output[0], output[1]
            trunk_ports.append(port)
            cli = clicopy
            cli += 'trunk-modify name %s jumbo ' % trunk_name
            run_cli(module, cli)

    cli = clicopy
    cli += ' switch-local port-config-show format port no-show-headers'
    ports = run_cli(module, cli).split()
    ports_to_modify = list(set(ports) - set(trunk_ports))
    ports_to_modify = ','.join(ports_to_modify)
    cli = clicopy
    cli += ' switch-local port-config-modify port %s %s' \
           % (ports_to_modify, modify_flag)
    return run_cli(module, cli)


def configure_control_network(module, network):
    """
    Method to configure the fabric control network.
    :param module: The Ansible module to fetch input parameters.
    :param network: It can be in-band or management.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    cli += ' fabric-info format control-network '
    current_control_network = run_cli(module, cli).split()

    if len(current_control_network) == 1:
        cli = pn_cli(module)
        cli += ' fabric-local-modify control-network ' + network
        return run_cli(module, cli)
    elif current_control_network[1] != network:
        cli = pn_cli(module)
        cli += ' fabric-local-modify control-network ' + network
        return run_cli(module, cli)
    else:
        return ' Already configured '


def enable_ports(module):
    """
    Method to enable all ports of a switch.
    :param module: The Ansible module to fetch input parameters.
    :return: The output of run_cli() method or None.
    """
    cli = pn_cli(module)
    clicopy = cli
    cli += ' switch-local port-config-show format enable no-show-headers '
    if 'off' in run_cli(module, cli).split():
        cli = clicopy
        cli += ' switch-local port-config-show format port no-show-headers '
        out = run_cli(module, cli)

        cli = clicopy
        cli += ' switch-local port-config-show format port speed 40g '
        cli += ' no-show-headers '
        out_40g = run_cli(module, cli)
        out_remove10g = []

        if len(out_40g) > 0 and out_40g != 'Success':
            out_40g = out_40g.split()
            out_40g = list(set(out_40g))
            if len(out_40g) > 0:
                for port_number in out_40g:
                    out_remove10g.append(str(int(port_number) + int(1)))
                    out_remove10g.append(str(int(port_number) + int(2)))
                    out_remove10g.append(str(int(port_number) + int(3)))

        if out:
            out = out.split()
            out = set(out) - set(out_remove10g)
            out = list(out)
            if out:
                ports = ','.join(out)
                cli = clicopy
                cli += ' switch-local port-config-modify port %s enable ' % (
                    ports)
                return run_cli(module, cli)
    else:
        return None


def create_or_join_fabric(module, fabric_name, fabric_network):
    """
    Method to create/join a fabric with default fabric type as mgmt.
    :param module: The Ansible module to fetch input parameters.
    :param fabric_name: Name of the fabric to create/join.
    :param fabric_network: Type of the fabric to create (mgmt/in-band).
    Default value: mgmt
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    clicopy = cli

    cli += ' fabric-show format name no-show-headers '
    existing_fabrics = run_cli(module, cli).split()

    if fabric_name not in existing_fabrics:
        cli = clicopy
        cli += ' fabric-create name ' + fabric_name
        cli += ' fabric-network ' + fabric_network
        return run_cli(module, cli)
    else:
        cli = clicopy
        cli += ' fabric-info format name no-show-headers'
        cli = shlex.split(cli)
        rc, out, err = module.run_command(cli)

        if err:
            cli = clicopy
            cli += ' fabric-join name ' + fabric_name
        elif out:
            present_fabric_name = out.split()
            if present_fabric_name[1] not in existing_fabrics:
                cli = clicopy
                cli += ' fabric-join name ' + fabric_name
            else:
                return 'Switch already in the fabric'

    return run_cli(module, cli)


def modify_auto_neg(module):
    """
    Module to enable/disable auto-neg for T2+ platforms.
    :param module:
    :return: Nothing
    """
    current_switch = module.params['pn_current_switch']
    spines = module.params['pn_spine_list']

    if current_switch in spines:
        cli = pn_cli(module)
        cli += ' switch-local bezel-portmap-show format port no-show-headers '
        cli = shlex.split(cli)
        out = module.run_command(cli)[1]
        all_ports = out.splitlines()
        all_ports = [port.strip() for port in all_ports]
        time.sleep(1)

        cli = pn_cli(module)
        cli += ' switch-local lldp-show format local-port no-show-headers '
        cli = shlex.split(cli)
        out = module.run_command(cli)[1]
        lldp_ports = out.splitlines()
        lldp_ports = [port.strip() for port in lldp_ports]
        time.sleep(1)

        idle_ports = list(set(all_ports) ^ set(lldp_ports))
        cli = pn_cli(module)
        cli += ' switch-local port-config-modify port %s autoneg ' % ','.join(idle_ports)
        cli = shlex.split(cli)
        module.run_command(cli)
        time.sleep(1)

        cli = pn_cli(module)
        cli += ' switch-local lldp-show format local-port no-show-headers '
        cli = shlex.split(cli)
        out = module.run_command(cli)[1]
        lldp_ports = out.splitlines()
        lldp_ports = [port.strip() for port in lldp_ports]
        time.sleep(1)

        idle_ports = list(set(all_ports) ^ set(lldp_ports))
        cli = pn_cli(module)
        cli += ' switch-local port-config-modify port %s no-autoneg ' % ','.join(idle_ports)
        module.run_command(cli)
        time.sleep(1)

        return "Auto-neg Configured"


def modify_auto_trunk(module, flag):
    """
    Method to enable/disable auto trunk setting of a switch.
    :param module: The Ansible module to fetch input parameters.
    :param flag: Enable/disable flag for the cli command.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    if flag.lower() == 'enable':
        cli += ' system-settings-modify auto-trunk '
        return run_cli(module, cli)
    elif flag.lower() == 'disable':
        cli += ' system-settings-modify no-auto-trunk '
        return run_cli(module, cli)


def enable_web_api(module):
    """
    Method to enable web api on switches.
    :param module: The Ansible module to fetch input parameters.
    """
    cli = pn_cli(module)
    cli += ' admin-service-modify web if mgmt '
    run_cli(module, cli)


def toggle(module, curr_switch, toggle_ports, toggle_speed, port_speed, splitter_ports, quad_ports):
    """
    Method to toggle ports for topology discovery
    :param module: The Ansible module to fetch input parameters.
    :return: The output messages for assignment.
    :param curr_switch on which we run toggle.
    :param toggle_ports to be toggled.
    :param toggle_speed to which ports to be toggled.
    :param splitter_ports are splitter ports
    """
    output = ''
    cli = pn_cli(module)
    clicopy = cli

    for speed in toggle_speed:
        if int(port_speed.strip('g'))/int(speed.strip('g')) >= 4:
            is_splittable = True
        else:
            is_splittable = False
        cli = clicopy
        cli += 'switch %s lldp-show format local-port ' % curr_switch
        cli += 'parsable-delim ,'
        local_ports = run_cli(module, cli).split()

        _undiscovered_ports = sorted(list(set(toggle_ports) - set(local_ports)),
                                     key=lambda x: int(x))
        non_splittable_ports = []
        undiscovered_ports = []

        for _port in _undiscovered_ports:
            if splitter_ports.get(_port, 0) == 1:
                undiscovered_ports.append("%s-%s" % (_port, int(_port)+3))
            elif splitter_ports.get(_port, 0) == 0:
                undiscovered_ports.append(_port)
            else:
                # Skip intermediate splitter ports
                continue
            if not is_splittable:
                non_splittable_ports.append(_port)
        undiscovered_ports = ",".join(undiscovered_ports)

        if not undiscovered_ports:
            continue

        cli = clicopy
        cli += 'switch %s port-config-modify port %s ' % (curr_switch, undiscovered_ports)
        cli += 'disable'
        run_cli(module, cli)

        if non_splittable_ports:
            non_splittable_ports = ",".join(non_splittable_ports)
            cli = clicopy
            cli += 'switch %s port-config-modify ' % curr_switch
            cli += 'port %s ' % non_splittable_ports
            cli += 'speed %s enable' % speed
            run_cli(module, cli)
        else:
            cli = clicopy
            cli += 'switch %s port-config-modify ' % curr_switch
            cli += 'port %s ' % undiscovered_ports
            cli += 'speed %s enable' % speed
            run_cli(module, cli)

        time.sleep(10)

    # Revert undiscovered ports back to their original speed
    cli = clicopy
    cli += 'switch %s lldp-show format local-port ' % curr_switch
    cli += 'parsable-delim ,'
    local_ports = run_cli(module, cli).split()
    _undiscovered_ports = sorted(list(set(toggle_ports) - set(local_ports)),
                                 key=lambda x: int(x))
    disable_ports = []
    undiscovered_ports = []
    for _port in _undiscovered_ports:
        if _port in quad_ports:
            disable_ports.append(str(_port))
            # dont add to undiscovered ports
        elif splitter_ports.get(_port, 0) == 1:
            disable_ports.append("%s-%s" % (_port, int(_port)+3))
            undiscovered_ports.append(_port)
        elif splitter_ports.get(_port, 0) == 0:
            disable_ports.append(str(_port))
            undiscovered_ports.append(_port)
        else:
            # Skip intermediate splitter ports
            pass

    disable_ports = ",".join(disable_ports)
    if disable_ports:
        cli = clicopy
        cli += 'switch %s port-config-modify port %s disable' % (curr_switch, disable_ports)
        run_cli(module, cli)

    undiscovered_ports = ",".join(undiscovered_ports)
    if not undiscovered_ports:
        return

    cli = clicopy
    cli += 'switch %s port-config-modify ' % curr_switch
    cli += 'port %s ' % undiscovered_ports
    cli += 'speed %s enable' % port_speed
    run_cli(module, cli)
    output += 'Toggle completed successfully '

    return output


def toggle_ports(module, curr_switch):
    """
    Method to discover the toggle ports.
    :param module: The Ansible module to fetch input parameters.
    :param curr_switch on which toggle discovery happens.
    """
    output = ''
    cli = pn_cli(module)
    clicopy = cli
    g_toggle_ports = {
        '25g': {'ports': [], 'speeds': ['10g']},
        '40g': {'ports': [], 'speeds': ['10g']},
        '100g': {'ports': [], 'speeds': ['10g', '25g', '40g']}
    }
    ports_25g = []
    ports_40g = []
    ports_100g = []

    cli += 'switch %s port-config-show format port,speed ' % curr_switch
    cli += 'parsable-delim ,'
    max_ports = run_cli(module, cli).split()

    all_next_ports = []
    for port_info in max_ports:
        if port_info:
            port, speed = port_info.strip().split(',')
            all_next_ports.append(str(int(port)+1))
            if g_toggle_ports.get(speed, None):
                g_toggle_ports[speed]['ports'].append(port)

    # Get info on splitter ports
    g_splitter_ports = {}
    all_next_ports = ','.join(all_next_ports)
    cli = clicopy
    cli += 'switch %s port-show port %s format ' % (curr_switch, all_next_ports)
    cli += 'port,bezel-port parsable-delim ,'
    splitter_info = run_cli(module, cli).split()

    for sinfo in splitter_info:
        if not sinfo:
            break
        _port, _sinfo = sinfo.split(',')
        _port = int(_port)
        if '.2' in _sinfo:
            for i in range(4):
                g_splitter_ports[str(_port-1 + i)] = 1 + i

    # Get info on Quad Ports
    g_quad_ports = {'25g': []}
    cli = clicopy
    cli += 'switch %s switch-info-show format model, layout horizontal ' % curr_switch
    cli += 'parsable-delim ,'
    model_info = run_cli(module, cli).split()

    for modinfo in model_info:
        if not modinfo:
            break
        model = modinfo
        if model == "ACCTON-AS7316-54X" and g_toggle_ports.get('25g', None):
            for _port in g_toggle_ports['25g']['ports']:
                if _port not in g_splitter_ports:
                    g_quad_ports['25g'].append(_port)

    for port_speed, port_info in g_toggle_ports.iteritems():
        if port_info['ports']:
            output += toggle(module, curr_switch, port_info['ports'], port_info['speeds'], port_speed,
                             g_splitter_ports, g_quad_ports.get(port_speed, []))

    return output


def assign_ipv6_address(module, ipv6_address, current_switch, ip_type):
    """
    Add loopback interface and router id to vrouters.
    :param module: The Ansible module to fetch input parameters.
    :param ipv6_address: The loopback ip to be assigned.
    :param current_switch: The name of current running switch.
    :param ip_type: ip type inband/mgmt.
    :return: String describing if loopback ip/router id got assigned or not.
    """
    global CHANGED_FLAG
    output = ''

    leaf_list = module.params['pn_leaf_list']
    spine_list = module.params['pn_spine_list']
    cli = pn_cli(module)

    if current_switch in spine_list:
        count = spine_list.index(current_switch)
    elif current_switch in leaf_list:
        count = leaf_list.index(current_switch) + 2

    if ipv6_address:
        ipv6 = ipv6_address.split('/')
        subnet_ipv6 = ipv6[1]
        ipv6 = ipv6[0]
        ipv6 = ipv6.split(':')
        if not ipv6[-1]:
            ipv6[-1] = "0"
        host_count_ipv6 = int(ipv6[-1], 16)
        host_count_ipv6 += count
        ipv6[-1] = str(hex(host_count_ipv6)[2:])
        ipv6_ip = ':'.join(ipv6)

    cli = pn_cli(module)
    clicopy = cli
    cli += ' switch-local switch-setup-show format %s ' % ip_type
    existing_ip = run_cli(module, cli).split()

    if ipv6_address not in existing_ip:
        cli = clicopy
        cli += ' switch %s switch-setup-modify ' % current_switch
        cli += ' %s %s/%s ' % (ip_type, ipv6_ip, subnet_ipv6)
        run_cli(module, cli)
        CHANGED_FLAG.append(True)
        output += 'Assigned %s ip ' % ipv6_ip
    else:
        output += 'ip %s already assigned ' % ipv6_ip

    return output


def assign_inband_ipv4(module):

    global CHANGED_FLAG
    switches_list = []
    switch_ip = {}
    spines = module.params['pn_spine_list']
    leafs = module.params['pn_leaf_list']
    switch = module.params['pn_current_switch']

    if module.params['pn_inband_ipv4']:
        address = module.params['pn_inband_ipv4'].split('.')
        static_part = str(address[0]) + '.' + str(address[1]) + '.'
        static_part += str(address[2]) + '.'
        last_octet = str(address[3]).split('/')
        subnet = last_octet[1]
        count = int(last_octet[0])
    else:
        return 'in-band ipv4 not specified '

    if spines:
        switches_list += spines

    if leafs:
        switches_list += leafs


    for sw in switches_list:
        switch_ip[sw] = static_part + str(count) + '/' + subnet
        count += 1

    # Get existing in-band ip.
    cli = pn_cli(module)
    clicopy = cli
    cli += ' switch-local switch-setup-show format in-band-ip'
    existing_inband_ip = run_cli(module, cli).split()

    if switch_ip[switch] not in existing_inband_ip:
        cli = clicopy
        cli += ' switch %s switch-setup-modify ' % switch
        cli += ' in-band-ip ' + switch_ip[switch]
        run_cli(module, cli)
        CHANGED_FLAG.append(True)

    return 'Assigned in-band ip ' + switch_ip[switch]


def main():
    """ This section is for arguments parsing """
    module = AnsibleModule(
        argument_spec=dict(
            pn_fabric_name=dict(required=True, type='str'),
            pn_fabric_network=dict(required=False, type='str',
                                   choices=['mgmt', 'in-band'], default='mgmt'),
            pn_fabric_control_network=dict(required=False, type='str',
                                           choices=['mgmt', 'in-band'],
                                           default='mgmt'),
            pn_toggle_port_speed=dict(required=False, type='bool', default=True),
            pn_spine_list=dict(required=False, type='list', default=[]),
            pn_leaf_list=dict(required=False, type='list', default=[]),
            pn_inband_ipv4=dict(required=False, type='str', default='192.16.0.1/24'),
            pn_inband_ipv6=dict(required=False, type='str'),
            pn_mgmt_ip=dict(required=False, type='str'),
            pn_mgmt_ip_subnet=dict(required=False, type='str'),
            pn_mgmt_ipv6=dict(required=False, type='str'),
            pn_current_switch=dict(required=False, type='str'),
            pn_static_setup=dict(required=False, type='bool', default=False),
            pn_gateway_ip=dict(required=False, type='str'),
            pn_dns_ip=dict(required=False, type='str'),
            pn_dns_secondary_ip=dict(required=False, type='str'),
            pn_domain_name=dict(required=False, type='str'),
            pn_ntp_server=dict(required=False, type='str'),
            pn_web_api=dict(type='bool', default=True),
            pn_stp=dict(required=False, type='bool', default=True),
            pn_autotrunk=dict(required=False, type='str',
                              choices=['enable', 'disable']),
            pn_autoneg=dict(required=False, type='bool')
        )
    )

    fabric_name = module.params['pn_fabric_name']
    fabric_network = module.params['pn_fabric_network']
    control_network = module.params['pn_fabric_control_network']
    toggle_flag = module.params['pn_toggle_port_speed']
    current_switch = module.params['pn_current_switch']
    autotrunk = module.params['pn_autotrunk']
    autoneg = module.params['pn_autoneg']
    mgmt_ipv6 = module.params['pn_mgmt_ipv6']
    in_band_ipv6 = module.params['pn_inband_ipv6']
    results = []
    global CHANGED_FLAG

    # Make switch setup static
    if module.params['pn_static_setup']:
        make_switch_setup_static(module)

    # Update switch names to match host names from hosts file
    if 'Updated' in update_switch_names(module, current_switch):
        CHANGED_FLAG.append(True)

    # Create/join fabric
    if 'created' in create_or_join_fabric(module, fabric_name,
                                          fabric_network):
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': u"Created fabric '{}'".format(fabric_name)
        })
    else:
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': u"Joined fabric '{}'".format(fabric_name)
        })

    # Modify auto-neg for T2+ platforms
    if autoneg is True and current_switch in module.params['pn_spine_list']:
        out = modify_auto_neg(module)
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': out
        })

    # Configure fabric control network to either mgmt or in-band
    if 'Success' in configure_control_network(module, control_network)\
    or 'created' in configure_control_network(module, control_network):
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': u"Configured fabric control network to '{}'".format(
                control_network)
        })

    # Enable/disable auto-trunk
    if autotrunk:
        modify_auto_trunk(module, autotrunk)
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': u"Auto-trunk {}d".format(autotrunk)
        })

    # Enable web api if flag is True
    if module.params['pn_web_api']:
        enable_web_api(module)

    # Enable STP
    if 'Success' in modify_stp_local(module, 'enable'):
        CHANGED_FLAG.append(True)

    # Enable jumbo flag
    if 'Success' in ports_modify_jumbo(module, 'jumbo'):
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': 'Jumbo enabled in ports'
        })

    # Enable ports
    if enable_ports(module):
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': 'Ports enabled'
        })

    # Toggle 40g/100g ports to 10g/25g
    if toggle_flag:
        out = toggle_ports(module, module.params['pn_current_switch'])
        CHANGED_FLAG.append(True)
        results.append({
            'switch': current_switch,
            'output': out
        })

    # Assign in-band ipv4.
    out = assign_inband_ipv4(module)
    results.append({
        'switch': current_switch,
        'output': out
    })

    # Assign mgmt ipv6.
    if mgmt_ipv6:
        out = assign_ipv6_address(module, mgmt_ipv6, current_switch, "mgmt-ip6")
        results.append({
            'switch': current_switch,
            'output': out
        })


    # Enable STP if flag is True
    if module.params['pn_stp']:
        if 'Success' in modify_stp_local(module, 'enable'):
            CHANGED_FLAG.append(True)
            results.append({
                'switch': current_switch,
                'output': 'STP enabled'
            })

    # Exit the module and return the required JSON
    module.exit_json(
        unreachable=False,
        msg='Fabric creation succeeded',
        summary=results,
        exception='',
        task='Fabric creation',
        failed=False,
        changed=True if True in CHANGED_FLAG else False
    )

if __name__ == '__main__':
    main()

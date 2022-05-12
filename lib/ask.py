##
##

import logging
import sys
import ipaddress
import getpass
from distutils.util import strtobool


class ask(object):
    type_list = 0
    type_dict = 1

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def divide_list(self, array, n):
        for i in range(0, len(array), n):
            yield array[i:i + n]

    def get_option_struct_type(self, options):
        if options:
            if len(options) > 0:
                if type(options[0]) is dict:
                    self.logger.info("get_option_struct_type: options provided as type dict")
                    return 1, len(options)
                elif type(options) is list:
                    self.logger.info("get_option_struct_type: options provided as a list")
                    return 0, len(options)
                else:
                    raise Exception("get_option_struct_type: unknown options data type")
        raise Exception("ask: no options to select from")

    def get_option_text(self, options, option_type, index=0):
        if option_type == ask.type_dict:
            return options[index]['name']
        else:
            return options[index]

    def ask_list(self, question, options=[], descriptions=[], default=None):
        """Get selection from list"""
        list_incr = 15
        answer = None
        input_list = []
        option_width = 0
        description_width = 0
        option_type, list_lenghth = self.get_option_struct_type(options)
        print("%s:" % question)
        if default:
            self.logger.info("ask_list: checking default value %s" % default)
            if option_type == ask.type_dict:
                default_selection = next((i for i, item in enumerate(options) if item['name'] == default), None)
            else:
                default_selection = next((i for i, item in enumerate(options) if item == default), None)
            if default_selection is not None:
                if self.ask_yn("Use previous value: \"%s\"" % default, default=True):
                    return default_selection
        if list_lenghth == 1:
            print("Auto selecting the only option available => %s" % self.get_option_text(options, option_type))
            return 0
        for i, item in enumerate(options):
            if type(item) is dict:
                if len(item['name']) > option_width:
                    option_width = len(item['name'])
                if 'description' in item:
                    if len(item['description']) > description_width:
                        description_width = len(item['description'])
                input_list.append((i, item['name'], item['description'] if 'description' in item else None))
            else:
                if len(item) > option_width:
                    option_width = len(item)
                if i < len(descriptions):
                    if len(descriptions[i]) > description_width:
                        description_width = len(descriptions[i])
                input_list.append((i, item, descriptions[i] if i < len(descriptions) else None))
        divided_list = list(self.divide_list(input_list, list_incr))
        while True:
            last_group = False
            for count, sub_list in enumerate(divided_list):
                suffix = " {:-^{n}}".format('', n=description_width) if description_width > 0 else ""
                print("---- " + "{:-^{n}}".format('', n=option_width) + suffix)
                for item_set in sub_list:
                    suffix = " {}".format(item_set[2]) if item_set[2] else ""
                    print("{:d}) ".format(item_set[0] + 1).rjust(5) + "{}".format(item_set[1]).ljust(option_width) + suffix)
                if count == len(divided_list) - 1:
                    answer = input("Selection [q=quit]: ")
                    last_group = True
                else:
                    answer = input("Selection [n=next, q=quit]: ")
                answer = answer.rstrip("\n")
                if answer == 'n' and not last_group:
                    continue
                elif answer == 'q':
                    sys.exit(0)
                else:
                    break
            try:
                value = int(answer)
                if value > 0 and value <= len(options):
                    return value - 1
                else:
                    raise Exception
            except Exception:
                print("Please select the number corresponding to your selection.")
                continue

    def ask_long_list(self, question, options=[], descriptions=[], separator='.'):
        merged_list = [(options[i], descriptions[i]) for i in range(len(options))]
        sorted_list = sorted(merged_list, key=lambda option: option[0])
        options, descriptions = map(list, zip(*sorted_list))
        subselection_list = []
        new_option_list = []
        new_description_list = []
        for item in options:
            prefix = item.split(separator)[0]
            subselection_list.append(prefix)
        subselection_list = sorted(set(subselection_list))
        selection = self.ask_list(question + ' subselection', subselection_list)
        limit_prefix = subselection_list[selection]
        for i in range(len(options)):
            if options[i].startswith(limit_prefix + separator):
                new_option_list.append(options[i])
                if i < len(descriptions):
                    new_description_list.append(descriptions[i])
        selection = self.ask_list(question, new_option_list, new_description_list)
        return new_option_list[selection]

    def ask_quantity(self, options=[], mode=1, cpu_count=None):
        """Get CPU or Memory count"""
        list_incr = 15
        last_group = False
        num_list = []
        prompt_text = ""
        try:
            if mode == 1:
                prompt_text = 'Select the desired CPU count'
                for item in options:
                    num = str(item['cpu'])
                    if next((item for item in num_list if item[0] == num), None):
                        continue
                    if num == "1":
                        label = "CPU"
                    else:
                        label = "CPUs"
                    item_set = (num, label)
                    num_list.append(item_set)
            if mode == 2:
                prompt_text = 'Select the desired RAM size'
                for item in options:
                    num = item['mem']
                    if not next((item for item in options if item['mem'] == num and item['cpu'] == cpu_count), None):
                        continue
                    num = "{:g}".format(num / 1024)
                    if next((item for item in num_list if item[0] == num), None):
                        continue
                    label = "GiB"
                    item_set = (num, label)
                    num_list.append(item_set)
        except KeyError:
            raise Exception("ask_quantity: invalid options argument")
        if len(num_list) == 1:
            return 0
        print("%s:" % prompt_text)
        num_list = sorted(num_list, key=lambda x: float(x[0]))
        divided_list = list(self.divide_list(num_list, list_incr))
        while True:
            for count, sub_list in enumerate(divided_list):
                for item_set in sub_list:
                    suffix = item_set[1].rjust(len(item_set[1]) + 1)
                    print(item_set[0].rjust(10) + suffix)
                if count == len(divided_list) - 1:
                    answer = input("Selection [q=quit]: ")
                    last_group = True
                else:
                    answer = input("Selection [n=next, q=quit]: ")
                answer = answer.rstrip("\n")
                if answer == 'n' and not last_group:
                    continue
                if answer == 'q':
                    sys.exit(0)
                try:
                    find_answer = next((item for item in num_list if item[0] == answer), None)
                    if find_answer:
                        if mode == 2:
                            multiplier = float(answer)
                            value = int(multiplier * 1024)
                        else:
                            value = int(answer)
                        return value
                    else:
                        raise Exception
                except Exception:
                    print("Please select a value from the list.")
                    continue

    def ask_machine_type(self, question, options=[], default=None):
        """Get Cloud instance type by selecting CPU and Memory"""
        name_list = []
        description_list = []
        select_list = []
        print("%s:" % question)
        if default:
            self.logger.info("ask_machine_type: checking default value %s" % default)
            default_selection = next((i for i, item in enumerate(options) if item['name'] == default), None)
            if default_selection:
                if self.ask_yn("Use previous value: \"%s\"" % default, default=True):
                    return default_selection
        num_cpu = self.ask_quantity(options, 1)
        num_mem = self.ask_quantity(options, 2, cpu_count=num_cpu)
        try:
            for i in range(len(options)):
                if options[i]['cpu'] == num_cpu and options[i]['mem'] == num_mem:
                    name_list.append(options[i]['name'])
                    if 'description' in options[i]:
                        description_list.append(options[i]['description'])
                    select_list.append(i)
        except KeyError:
            raise Exception("ask_machine_type: invalid options argument")
        if len(description_list) > 0:
            selection = self.ask_list(question, name_list, description_list)
        else:
            selection = self.ask_list(question, name_list)
        return select_list[selection]

    def ask_text(self, question, recommendation=None, default=None):
        """Get text input"""
        print("%s:" % question)
        if default:
            if self.ask_yn("Use previous value: \"%s\"" % default, default=True):
                return default
        while True:
            if recommendation:
                suffix = ' [q=quit enter="' + recommendation + '"]'
            else:
                suffix = ' [q=quit]'
            prompt = 'Selection' + suffix + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if answer == 'q':
                sys.exit(0)
            if len(answer) > 0:
                return answer
            else:
                if recommendation:
                    return recommendation
                else:
                    print("Response can not be empty.")
                    continue

    def ask_pass(self, question, verify=True, default=None):
        if default:
            if self.ask_yn("Use previously stored password", default=True):
                return default

        while True:
            passanswer = getpass.getpass(prompt=question + ': ')
            passanswer = passanswer.rstrip("\n")
            if verify:
                checkanswer = getpass.getpass(prompt="Re-enter password: ")
                checkanswer = checkanswer.rstrip("\n")
                if passanswer == checkanswer:
                    break
                else:
                    print(" [!] Passwords do not match, please try again ...")
            else:
                break

        return passanswer

    def ask_yn(self, question, default=False):
        if default:
            default_answer = 'y'
        else:
            default_answer = 'n'
        while True:
            prompt = "{} (y/n) [{}]? ".format(question, default_answer)
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                answer = default_answer
            if answer == 'Y' or answer == 'y' or answer == 'yes':
                return True
            elif answer == 'N' or answer == 'n' or answer == 'no':
                return False
            else:
                print(" [!] Unrecognized answer, please try again...")

    def ask_ip(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            try:
                ip = ipaddress.ip_address(answer)
                return answer
            except ValueError:
                print("%s does not appear to be an IP address." % answer)
                continue

    def ask_net(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            try:
                net = ipaddress.ip_network(answer)
                return answer
            except ValueError:
                print("%s does not appear to be an IP network." % answer)
                continue

    def ask_net_range(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                return None
            try:
                (first, last) = answer.split('-')
                ip_first = ipaddress.ip_address(first)
                ip_last = ipaddress.ip_address(last)
                return answer
            except Exception:
                print("Invalid input, please try again...")
                continue

    def ask_bool(self, question, recommendation='true', default=None):
        """Get true or false response"""
        print("%s:" % question)
        if default:
            if self.ask_yn("Use previous value: \"%s\"" % default, default=True):
                return bool(strtobool(default))
        while True:
            if recommendation:
                suffix = ' [q=quit enter="' + recommendation + '"]'
            else:
                suffix = ' [q=quit]'
            prompt = 'Selection' + suffix + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if answer == 'q':
                sys.exit(0)
            if len(answer) == 0:
                answer = recommendation
            try:
                if answer == 'true' or answer == 'false':
                    return bool(strtobool(answer))
                else:
                    raise Exception("please answer true or false")
            except Exception as e:
                print("Invalid input: %s, please try again..." % str(e))
                continue

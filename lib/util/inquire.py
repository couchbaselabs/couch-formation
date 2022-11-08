##
##

import logging
import sys
import ipaddress
import getpass
import re
from typing import Union, Iterable
from distutils.util import strtobool


class Inquire(object):
    type_list = 0
    type_dict = 1

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def divide_list(array: list, n: int) -> Iterable:
        for i in range(0, len(array), n):
            yield array[i:i + n]

    @staticmethod
    def field_lengths(table: list[dict]) -> tuple[int]:
        vector = []
        row_len = 0
        for item in table:
            columns = ()
            for n, key in enumerate(item.keys()):
                lk = len(key)
                lv = len(item[key])
                lt = lk if lk > lv else lv
                columns = columns + (lt,)
            row_len = len(columns)
            vector.append(columns)

        final = ()
        for x in range(row_len):
            max_value = max(vector, key=lambda t: t[x])
            final = final + (max_value[x],)

        return final

    @staticmethod
    def print_header(t: tuple, row: dict, pad: int = 5) -> None:
        print("#".ljust(pad+2), end='')
        for n, key in enumerate(row.keys()):
            print(key.capitalize().ljust(t[n]), end='')
            print(" ", end='')
        print("")
        print("-" * (pad+1), end='')
        print(" ", end='')
        for n, value in enumerate(t):
            print("-" * value, end='')
            print(" ", end='')
        print("")

    @staticmethod
    def print_line(t: tuple, row: dict, item: int, pad: int = 5) -> None:
        print(f"{str(item).rjust(pad)}) ", end='')
        for n, key in enumerate(row.keys()):
            print(str(row[key]).ljust(t[n]), end='')
            print(" ", end='')
        print("")

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
        if option_type == Inquire.type_dict:
            return options[index]['name']
        else:
            return options[index]

    def ask_list_basic(self, question: str, options: list[str], page_length: int = 20) -> str:
        print("%s:" % question)
        divided_list = list(self.divide_list(options, page_length))
        while True:
            last_group = False
            answer = ''
            for count, sub_list in enumerate(divided_list):
                page_incr = count * page_length
                for n, item in enumerate(sub_list):
                    item_number = n + 1 + page_incr
                    print(f"{str(item_number).rjust(5)}) {item}")

                if count == len(divided_list) - 1:
                    answer = input("Selection [q=quit]: ")
                    last_group = True
                else:
                    answer = input("Selection [n=next, q=quit]: ")

                answer = answer.rstrip("\n")

                if (answer == 'n' or answer == '') and not last_group:
                    continue
                elif answer == 'q':
                    sys.exit(0)
                else:
                    break

            try:
                response = int(answer)
                if 0 < response <= len(options):
                    return options[response - 1]
                else:
                    raise ValueError
            except ValueError:
                print("Please select the number corresponding to your selection.")
                continue

    def ask_list_dict(self, question: str, options: list[dict], sort_key: Union[str, None] = None, page_length: int = 20) -> dict:
        if sort_key:
            options = sorted(options, key=lambda i: i[sort_key] if i[sort_key] else "")

        print("%s:" % question)

        divided_list = list(self.divide_list(options, page_length))
        field_length = self.field_lengths(options)
        while True:
            last_group = False
            answer = ''
            for count, sub_list in enumerate(divided_list):
                page_incr = count * page_length
                self.print_header(field_length, sub_list[0])
                for n, item in enumerate(sub_list):
                    item_number = n + 1 + page_incr
                    self.print_line(field_length, item, item_number)

                if count == len(divided_list) - 1:
                    answer = input("Selection [q=quit]: ")
                    last_group = True
                else:
                    answer = input("Selection [n=next, q=quit]: ")

                answer = answer.rstrip("\n")

                if (answer == 'n' or answer == '') and not last_group:
                    continue
                elif answer == 'q':
                    sys.exit(0)
                else:
                    break

            try:
                response = int(answer)
                if 0 < response <= len(options):
                    return options[response - 1]
                else:
                    raise ValueError
            except ValueError:
                print("Please select the number corresponding to your selection.")
                continue

    def ask_list(self, question, options=[], descriptions=[], list_only=False, page_len=20, default=None):
        """Get selection from list"""
        list_incr = page_len
        answer = None
        input_list = []
        option_width = 0
        description_width = 0
        date_width = 0
        option_type, list_length = self.get_option_struct_type(options)
        print("%s:" % question)
        if default:
            self.logger.info("ask_list: checking default value %s" % default)
            if option_type == Inquire.type_dict:
                default_selection = next((i for i, item in enumerate(options) if item['name'] == default), None)
            else:
                default_selection = next((i for i, item in enumerate(options) if item == default), None)
            if default_selection is not None:
                if self.ask_yn("Use default value: \"%s\"" % default, default=True):
                    return default_selection
        if list_length == 1:
            print("Auto selecting the only option available => %s" % self.get_option_text(options, option_type))
            return 0
        for i, item in enumerate(options):
            if type(item) is dict:
                if len(item['name']) > option_width:
                    option_width = len(item['name'])
                if 'description' in item:
                    if len(item['description']) > description_width:
                        description_width = len(item['description'])
                if 'datetime' in item:
                    date_width = 20
                input_list.append((i, item['name'], item['description'] if 'description' in item else None, item['datetime'] if 'datetime' in item else None))
            else:
                if len(item) > option_width:
                    option_width = len(item)
                if i < len(descriptions):
                    if len(descriptions[i]) > description_width:
                        description_width = len(descriptions[i])
                input_list.append((i, item, descriptions[i] if i < len(descriptions) else None, None))
        divided_list = list(self.divide_list(input_list, list_incr))
        while True:
            last_group = False
            for count, sub_list in enumerate(divided_list):
                suffix = " {:-^{n}}".format('', n=description_width) if description_width > 0 else ""
                date_txt = " {:-^{n}}".format('', n=date_width) if date_width > 0 else ""
                print("---- " + "{:-^{n}}".format('', n=option_width) + suffix + date_txt)

                for item_set in sub_list:
                    suffix = " {}".format(item_set[2]).ljust(description_width + 1) if item_set[2] else "{: ^{n}}".format('', n=description_width+1)
                    date_txt = f" {item_set[3].strftime('%D %r')}" if item_set[3] else ""
                    print("{:d}) ".format(item_set[0] + 1).rjust(5) + "{}".format(item_set[1]).ljust(option_width) + suffix + date_txt)

                if count == len(divided_list) - 1:
                    if list_only:
                        return
                    answer = input("Selection [q=quit]: ")
                    last_group = True
                else:
                    answer = input("Selection [n=next, q=quit]: ")

                answer = answer.rstrip("\n")

                if (answer == 'n' or answer == '') and not last_group:
                    continue
                elif answer == 'q':
                    if list_only:
                        return
                    else:
                        sys.exit(0)
                else:
                    break

            if list_only:
                return

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

    @staticmethod
    def ask_bool(question, recommendation='true') -> bool:
        if bool(strtobool(recommendation)):
            default_answer = 'y'
        else:
            default_answer = 'n'

        print("%s:" % question)
        while True:
            if recommendation:
                suffix = ' (y/n) [q=quit enter="' + default_answer + '"]'
            else:
                suffix = ' [q=quit]'
            prompt = 'Selection' + suffix + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if answer == 'q':
                sys.exit(0)
            if len(answer) == 0:
                answer = default_answer
            try:
                return bool(strtobool(answer))
            except Exception as e:
                print("Invalid input: %s, please try again..." % str(e))
                continue

    def ask_multi(self, question, options=[], default=[]):
        selections = []
        used_numbers = []
        print("%s:" % question)
        for count, item in enumerate(options):
            print(f" {count+1}) {item}")
        while True:
            print(f"Selection: [{','.join(selections)}]")
            sys.stdout.write("\033[K")
            answer = input("Selection [d=done, q=quit]: ")
            answer = answer.rstrip("\n")
            if answer == "q":
                sys.exit(0)
            if answer == "d":
                if len(selections) == 0 and len(default) != 0:
                    selections = default
                break
            try:
                value = int(answer)
                if value not in used_numbers:
                    if value > 0 and value <= len(options):
                        selections.append(options[value - 1])
                        used_numbers.append(value)
                else:
                    raise Exception
            except Exception:
                pass
            sys.stdout.write("\x1b[A")
            sys.stdout.write("\x1b[A")
        return selections

    def ask_search(self, question, options=[]):
        print("%s:" % question)
        while True:
            sub_options = []
            answer = input("Search term [q=quit]: ")
            answer = answer.rstrip("\n")
            if answer == "q":
                sys.exit(0)
            for option in options:
                p = re.compile(answer)
                if p.match(option["name"]):
                    sub_options.append(option)
            if len(sub_options) == 0:
                print("Search term not found.")
                continue
            while True:
                for count, item in enumerate(sub_options):
                    print(f" {count+1}) {item['name']} ({item['description']})")
                answer = input("Selection [r=retry, q=quit]: ")
                answer = answer.rstrip("\n")
                if answer == "q":
                    sys.exit(0)
                if answer == "r":
                    break
                try:
                    value = int(answer)
                    if value > 0 and value <= len(options):
                        return sub_options[value - 1]
                    else:
                        raise Exception
                except Exception:
                    print("Please select the number corresponding to your selection.")
                    continue
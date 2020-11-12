from elaspic_rest_api.jobsubmitter.jobsubmitter import parse_input_data
from elaspic_rest_api.jobsubmitter.submit import create_qsub_system_command


def test_create_qsub_system_command(data_in):
    items_list = parse_input_data(data_in)
    for items in items_list:
        s, m, muts = items
        for item in [s, m] + list(muts):
            system_command = create_qsub_system_command(item)
            print(system_command)

"""
===================
Bioscrape Connector
===================

run with:
> python -m vivarium_bioscrape.composites.bioscrape_connector
"""
import os

import numpy as np

# vivarium core imports
from vivarium.core.experiment import pp
from vivarium.core.process import Generator
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    COMPARTMENT_OUT_DIR,
)
from vivarium.plots.simulation_output import plot_simulation_output
from vivarium.library.dict_utils import deep_merge

# import processes
from vivarium_bioscrape.composites.composite_general import insert_topology
from vivarium_bioscrape.processes.bioscrape import Bioscrape, get_model_species_ids
from vivarium_bioscrape.processes.one_way_map import OneWayMap
from vivarium_bioscrape.library.schema import array_from, array_to

NAME = 'bioscrape_connector'


class BioscrapeConnector(Generator):
    name = NAME
    defaults = {
        'models': {},
        'connections': [],
        }

    def __init__(self, config=None, models=None, connections=None):
        if config is None:
            config = {}

        if 'models' not in config:
            config['models'] = models
        if 'connections' not in config:
            config['connections'] = connections

        super(BioscrapeConnector, self).__init__(config)
        self.topology = self.initial_topology(self.config)

    def initial_state(self, config=None):
        # TODO -- find and resolve conflicts
        network = self.generate()
        processes = network['processes']

        # make initial state by merging initial states of processes
        initial_state = {}
        for name, process in self.models.items():
            initial = process.initial_state()
            initial_with_store = {
                f'{name}_{store}': values
                for store, values in initial.items()}
            initial_state = deep_merge(initial_state, initial_with_store)

        # TODO -- after going through map, values need to be the same on either side
        # TODO -- throw an exception, make them fix it
        # for name, process in self.connections.items():
        #     config = process.parameters

        return initial_state

    def generate_processes(self, config):

        # make bioscrape processes
        models = {
            name: Bioscrape(parameters)
            for name, parameters in config['models'].items()}

        # make connection processes
        connections = {}
        for connection in config['connections']:
            source = connection['source']
            target = connection['target']
            map = connection['map']

            source_species = models[source].get_species_names()
            target_species = models[target].get_species_names()

            connector_config = {
                'source_keys': source_species,
                'target_keys': target_species,
                'map': map}
            connections[f'{source}_{target}_connector'] = OneWayMap(connector_config)

        self.models = models
        self.connections = connections

        # combine model and connection processes
        return {**models, **connections}

    def generate_topology(self, config):
        return self.topology

    def initial_topology(self, config):

        # connect the models with their stores
        models = {
            name: {
                'species': (f'{name}_species',),
                'delta_species': (f'{name}_deltas',),
                'rates': (f'{name}_rates',)}
            for name, path in config['models'].items()}

        # make connections between model stores
        connections = {}
        for connection in config['connections']:
            source = connection['source']
            target = connection['target']
            connections[f'{source}_{target}_connector'] = {
                'source_deltas': (f'{source}_deltas',),
                'target_state': (f'{target}_species',),
            }

        return {**models, **connections}

    def add_model(self):
        # TODO -- to pass models in by name
        # TODO add to self.models
        pass

    def add_connection(self):
        # TODO add to self.connections
        pass

    def add_mappings(self, config=None, model=None, species=None, rates=None):
        if config is None:
            config = {}

        if model not in config:
            if species:
                config[model] = {
                    'species': species}
            if rates:
                config[model] = {
                    'rates': rates}
        elif model:
            raise ValueError('config and model keywords are conflicting for {}'.format(model))

        for model_path, port in config.items():
            for port_key, mappings in port.items():
                for mapping in mappings:
                    self.insert_topology(model_path, port_key, mapping)

    def insert_topology(self, model_path, port_key, mapping):
        self.topology[model_path][port_key] = insert_topology(
            self.topology[model_path][port_key], mapping)



def main():
    '''Simulate the composite and plot results.'''

    # make an output directory to save plots
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    model1_keys = get_model_species_ids('Notebooks/model1.xml')
    model3_keys = get_model_species_ids('Notebooks/model3.xml')

    # define the projection
    model1_vector = np.array(['rna_T' == key for key in model1_keys])
    model3_vector = np.array(['rna_T' == key for key in model3_keys])
    projection_1_3 = np.outer(
        model1_vector/np.sum(model1_vector),
        model3_vector/np.sum(model3_vector))
    # projection_3_1 = np.outer(
    #     model3_vector/np.sum(model3_vector),
    #     model1_vector/np.sum(model1_vector))
    # TODO (William) HW -- is this needed?
    model3_vector2 = np.array(['rna' in key for key in model3_keys])
    projection_3_1 = np.outer(
        model3_vector2/np.sum(model3_vector2),
        model1_vector/np.sum(model1_vector))

    # define map function
    def map_1_3(states):
        input_array = array_from(states['source_deltas'])
        output_array = np.dot(input_array, projection_1_3)
        return array_to(model3_keys, output_array)

    def map_3_1(states):
        input_array = array_from(states['source_deltas'])
        output_array = np.dot(input_array, projection_3_1)
        return array_to(model1_keys, output_array)


    # configuration
    time_step = 10
    models = {
        '1': {
            'time_step': time_step,
            'sbml_file': 'Notebooks/model1.xml'},
        '3': {
            'time_step': time_step,
            'sbml_file': 'Notebooks/model3.xml'},
    }
    connections = [
        {'source': '1', 'target': '3', 'map': map_1_3},
        {'source': '3', 'target': '1', 'map': map_3_1}
    ]

    # make the composite
    composite = BioscrapeConnector(
        models=models,
        connections=connections,
    )

    # get processes and topology, print
    network = composite.generate()
    processes = network['processes']
    topology = network['topology']

    print('PROCESSES:')
    pp(processes)
    print('TOPOLOGY:')
    pp(topology)

    ## Run a simulation
    # initial state
    initial_state = composite.initial_state()
    initial_state['1_species']['dna_G'] = 1
    initial_state['1_species']['rna_T'] = 10

    # run a simulation
    sim_settings = {
        'total_time': 1000,
        'initial_state': initial_state}
    output = simulate_compartment_in_experiment(composite, sim_settings)

    # plot simulation output
    plot_settings = {}
    plot_simulation_output(output, plot_settings, out_dir)


if __name__ == '__main__':
    main()

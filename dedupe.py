#!/usr/bin/python3

import os
import sys

import hashlib
from itertools import groupby

class Population:
    _clusters = []

    def append(self, cluster):
        self._clusters.append(cluster)

    @property
    def cluster_sizes_string(self):
        unsorted_sizes = list(map(lambda cluster: cluster.file_count(), self._clusters))
        sizes = sorted(unsorted_sizes, reverse=True)
        return ", ".join(map(lambda i: str(i), sizes))

    @property
    def file_count(self):
        return sum(map(lambda cluster: cluster.file_count(), self._clusters))

    def print_clusters(self):
        print('{:s}Individual clusters:'.format(Util.indent1))
        for i in range(0, len(self._clusters)):
            print('    Cluster #{:d}:'.format(i))
            self._clusters[i].print_paths(indent=Util.indent3)

    def print_directory_summary(self):
        print('{:s}Cluster summary by directory:'.format(Util.indent1))
        dir_counts = {}
        for c in self._clusters:
            for p in c.paths():
                d = os.path.dirname(p)
                if d == '':
                    d = '.'
                if d not in dir_counts:
                    dir_counts[d] = 1
                else:
                    dir_counts[d] += 1
        dirs = sorted(dir_counts.keys(),
                      key=lambda k: dir_counts[k],
                      reverse=True)
        for d in dirs:
            print('{:s}Dupe count={:5d} Dir={:s}'.format(Util.indent2, dir_counts[d], d))

    def print_report(self):
        print('{:s}Population report:'.format(Util.indent0))
        print('{:s}Number of (clusters, files): ({:d}, {:d})'
              .format(Util.indent1, len(self._clusters), self.file_count))
        self.print_size_summary()
        self.print_directory_summary()

    def print_size_summary(self):
        size_str = self.cluster_sizes_string
        print('{:s}Cluster summary of cluster sizes: {:s}'
              .format(Util.indent1, size_str))

    def refine_by(self, key_func):
        next_gen_clusters = []
        for cluster in self._clusters:
            Util.show_progress()
            child_clusters = list(cluster.refined_nontrivial_clusters(key_func))
            next_gen_clusters.extend(child_clusters)
        self._clusters = next_gen_clusters
        Util.print_newline()


class Cluster:
    _paths = []

    def __init__(self, paths=[]):
        self._paths = paths

    def append_dir(self, d, do_recurse=True):
        Util.print_newline()
        Util.show_progress()
        for item in os.listdir(d):
            next_item = d + '/' + item
            if os.path.isfile(next_item):
                self.append_file(next_item)
            if os.path.isdir(next_item) and do_recurse:
                self.append_dir(next_item)

    def append_file(self, file):
        Util.show_progress()
        self._paths.append(file)

    def file_count(self):
        return len(self._paths)

    def paths(self):
        return self._paths

    def print_paths(self, indent=None):
        if indent is None:
            indent = Util.indent1
        for path in self._paths:
            print('{:s}Size={:10d}: File={:s}'
                  .format(indent, Util.get_file_size(path), path)
                  )

    # Return new clusters rather than modifying the original.
    #   * Optimized for case in which duplicates are rare
    def refined_nontrivial_clusters(self, key_func):
        sorted_file_paths = sorted(self._paths, key=key_func)
        for key, path_group in groupby(sorted_file_paths, key_func):
            paths = list(path_group)
            if len(paths) > 1:  # and fileSize > 0:
                yield Cluster(paths)


class Util:
    indent0 = ''
    indent1 = '  '
    indent2 = '    '
    indent3 = '      '

    @staticmethod
    def get_file_chunk_wrapper(chunk_size):
        def get_file_chunk(path):
            chunk = ''
            try:
                with open(path, 'rb') as f:
                    chunk = f.read(chunk_size)
            except:
                chunk = ''
            return chunk
        return get_file_chunk
        
    @staticmethod
    def get_file_size(path):
        try:
            statinfo = os.stat(path)
            size = statinfo.st_size
        except:
            size = -1
        return size

    @staticmethod
    def get_md5(path):
        chunk_size = 4096
        hash_func = hashlib.md5()
        with open(path, 'rb') as file:
            for chunk in iter(lambda: file.read(chunk_size), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def print_args(argv):
        for i in range(0, len(argv)):
            print('DEBUG: argv[{:d}]={:s}'.format(i, argv[i]))

    @staticmethod
    def print_newline():
        print('', end='\n')

    @staticmethod
    def show_progress():
        print('.', end='')


# TODO: Provide a GUI with information navigation.
# TODO:   * GUI use case: Find which directories are near-copies of each other
# TODO: Support more file comparison more methods
# TODO: Support custom ordering and/or cluster-dependent ordering of file comparison functions
def main():
    #  TODO: Tune for performance on representative test set
    chunk_size = 32
    # Util.printArgs(sys.argv)
    cluster = Cluster()
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        # Note: This includes symlinks.
        if os.path.isfile(arg):
            cluster.append_file(arg)
        elif os.path.isdir(arg):
            cluster.append_dir(arg, True)
        # else ignore
    Util.print_newline()
    print('Read in {:d} files'.format(cluster.file_count()))
    population = Population()
    population.append(cluster)
    print('Deduping by file size....')
    population.refine_by(Util.get_file_size)
    # population.print_report()
    print('Deduping by initial chunk....')
    population.refine_by(Util.get_file_chunk_wrapper(chunk_size))
    # population.print_report()
    print('Deduping by MD5....')
    population.refine_by(Util.get_md5)
    population.print_report()

if __name__ == '__main__':
    main()

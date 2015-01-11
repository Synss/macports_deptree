#!/usr/bin/env python
# Copyright (c) 2014, 2015 Mathias Laurin
# BSD 3-Clause License (http://opensource.org/licenses/BSD-3-Clause)

r"""Print all dependencies required to build a port as a graph.

Usage:
    port_deptree.py PORTNAME [VARIANTS ...]

Example:
    port_deptree.py irssi -perl | dot -Tpdf -oirssi.pdf
    port_deptree.py $(port echo requested and outdated)\
            | dot -Tpdf | open -fa Preview

"""
from __future__ import print_function
import sys
_stdout, sys.stdout = sys.stdout, sys.stderr
import subprocess
import threading
import six
from six.moves.queue import Queue
from altgraph import Dot, Graph, GraphError
__version__ = "0.8"


def _(bytes):
    return bytes.decode("utf-8")


class NodeData(object):

    __slots__ = ("has_children", "status")

    def __init__(self):
        self.has_children = False
        self.status = "missing"  # in (installed, outdated, missing)


class EdgeData(object):

    __slots__ = ("section",)

    def __init__(self, section):
        self.section = section


def get_deps(portname, variants):
    """Return `section, depname` dependents of `portname` with `variants`."""
    process = ["port", "deps", portname]
    process.extend(variants)
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        section, sep, children = _(line).partition(":")
        if not section.endswith("Dependencies"): continue
        for child in [child.strip() for child in children.split(",")]:
            yield section.split()[0].lower(), child


def make_graph(portname, variants, graph):
    """Traverse dependency tree of `portname` with `variants`.

    Args:
        portname (str): The name of a port.
        variants (list): The variants to apply to `portname`.

    Returns:
        Graph.Graph: The graph.

    """
    def call(cmd):
        return subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE).stdout.readlines()

    installed = set(_(line.split()[0]) for line in call("port echo installed"))
    outdated = set(_(line.split()[0]) for line in call("port echo outdated"))
    visited = set()
    def traverse(parent):
        """Recursively traverse dependencies to `parent`."""
        if parent in visited:
            return
        else:
            visited.add(parent)
        node_data = graph.node_data(parent)
        if parent in outdated:
            node_data.status = "outdated"
        elif parent in installed:
            node_data.status = "installed"
        for section, child in get_deps(parent.strip('"'), variants):
            if parent is not root:
                node_data.has_children = True
            if not child in graph:
                graph.add_node(child, NodeData())
            graph.add_edge(parent, child, EdgeData(section),
                           create_nodes=False)
            traverse(child)
    root = portname
    graph.add_node(root, NodeData())
    traverse(root)
    return graph


def make_dot(graph):
    """Convert the graph to a dot file.

    Node and edge styles is obtained from the corresponding data.

    Args:
        graph (Graph.Graph): The graph.

    Returns:
        Dot.Dot: The dot file generator.

    """
    dot = Dot.Dot(graph, graphtype="digraph")
    dot.style(overlap=False, bgcolor="transparent")
    for node, (__, __, node_data) in six.iteritems(graph.nodes):
        style = {"style": "filled"}
        style["shape"] = "circle" if node_data.has_children else "doublecircle"
        style["color"], style["fillcolor"] = dict(
            missing=("red", "moccasin"),
            outdated=("forestgreen", "lightblue")).get(node_data.status,
                                                       ("black", "white"))
        dot.node_style(node, **style)
    for head, tail, edge_data in six.itervalues(graph.edges):
        section = edge_data.section
        color = dict(library="black",
                     fetch="forestgreen",
                     extract="darkgreen",
                     build="blue",
                     runtime="red").get(section, "green")
        dot.edge_style(head, tail,
                       label=section if section != "library" else "",
                       color=color, fontcolor=color)
    return dot


def show_stats(graph):
    """Create and display stats from the `graph`."""
    installed = 0
    outdated = 0
    total = graph.number_of_nodes()
    stats = dict(missing=0,
                 installed=0,
                 outdated=0)
    for __, __, node_data in six.itervalues(graph.nodes):
        stats[node_data.status] += 1
    print("Total:", total,
          "(%i" % stats["outdated"], "upgrades,", stats["missing"], "new)",
          file=sys.stderr)


if __name__ == '__main__':
    graph = Graph.Graph()
    commandline = {}
    try:
        if not sys.argv[1:]:
            raise RuntimeError
        for arg in sys.argv[1:]:
            if arg.startswith("@"):
                continue
            elif not (arg.startswith("+") or arg.startswith("-")):
                portname = arg
                commandline[portname] = []
            else:
                commandline[portname].append(arg)
    except:
        print(__doc__, file=_stdout)
        exit(1)
    for portname, variants in six.iteritems(commandline):
        print("Calculating dependencies for", portname, *variants,
              file=sys.stderr)
        make_graph(portname, variants, graph)
    show_stats(graph)
    for line in make_dot(graph).iterdot():
        print(line, file=_stdout)
    _stdout.flush()

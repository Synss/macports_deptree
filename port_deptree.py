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


class Fillcolor(object):

    Not_Installed = "moccasin"
    Outdated = "lightblue"
    Default = "white"


class Color(object):

    Not_Installed = "red"
    Outdated = "forestgreen"
    Default = "black"


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
        style = graph.node_data(parent)
        if parent not in installed:
            style["fillcolor"] = Fillcolor.Not_Installed
            style["color"] = Color.Not_Installed
        elif parent in outdated:
            style["fillcolor"] = Fillcolor.Outdated
            style["color"] = Color.Outdated
        for section, child in get_deps(parent.strip('"'), variants):
            if parent is not root:
                style["shape"] = "circle"
            if not child in graph:
                graph.add_node(child, {})
            color = dict(library="black",
                         fetch="forestgreen",
                         extract="darkgreen",
                         build="blue",
                         runtime="red").get(section, "green")
            graph.add_edge(parent, child,
                           edge_data=dict(
                               color=color,
                               fontcolor=color,
                               label=section if section != "library" else "",
                           ),
                           create_nodes=False)
            traverse(child)
    root = portname
    graph.add_node(root, {})
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
    node_style = dict(style="filled", fillcolor=Fillcolor.Default,
                      shape="doublecircle")
    for node, (__, __, data) in six.iteritems(graph.nodes):
        style = node_style.copy()
        style.update(data)
        dot.node_style(node, **style)
    for head, tail, style in six.itervalues(graph.edges):
        dot.edge_style(head, tail, **style)
    return dot


def show_stats(graph):
    """Create and display stats from the `graph`."""
    stats = {Fillcolor.Not_Installed: 0,
             Fillcolor.Outdated: 0,
             Fillcolor.Default: 0}
    for __, __, data in six.itervalues(graph.nodes):
        stats[data.get("fillcolor", Fillcolor.Default)] += 1
    print("Total:", graph.number_of_nodes(),
          "(%i" % stats[Fillcolor.Outdated], "upgrades,",
          stats[Fillcolor.Not_Installed], "new)",
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

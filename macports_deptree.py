#!/usr/bin/env python
# Copyright (c) 2014, Mathias Laurin
# BSD 3-Clause License (http://opensource.org/licenses/BSD-3-Clause)

"""Print all dependencies required to build a port as a graph.

Usage:
    python macports_deptree.py PORTNAME [VARIANTS ...]

Example:
    python macports_deptree.py irssi -perl | dot -Tpdf -oirssi.pdf

"""
import sys
import subprocess
import pydot
__version__ = "0.2"


def is_installed(portname):
    """Return True if `portname` is installed, False otherwise."""
    process = ["port", "installed", portname]
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        return not line.startswith("None")


def get_deps(portname, variants):
    """Return `section, depname` dependents of `portname` with `variants`."""
    process = ["port", "deps", portname]
    process.extend(variants)
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        section, sep, children = line.partition(":")
        if not section.endswith("Dependencies"): continue
        for child in [child.strip() for child in children.split(",")]:
            yield section.split()[0].lower(), child


def make_tree(portname, variants):
    """Traverse dependency tree of `portname` with `variants`.

    Args:
        portname (str): The name of a port.
        variants (list): The variants to apply to `portname`.

    Returns:
        pydot.Dot: The graph.

    """
    graph = pydot.Dot(graph_type="digraph",
                      overlap=False,
                      bgcolor="transparent")
    graph.set_node_defaults(style="filled", fillcolor="white",
                            shape="doublecircle")
    def traverse(parent):
        """Recursively traverse dependencies to `parent`."""
        if parent.get_name() in (node.get_name() for node in graph.get_nodes()):
            return
        else:
            graph.add_node(parent)
        if not is_installed(parent.get_name().strip('"')):
            parent.set_fillcolor("lightyellow")
            parent.set_color("red")
        for section, portname in get_deps(
                parent.get_name().strip('"'), variants):
            child = pydot.Node(portname)
            if parent is not root:
                parent.set_shape("circle")
            edge = pydot.Edge(parent, child)
            color = dict(library="black",
                         fetch="forestgreen",
                         extract="darkgreen",
                         build="blue",
                         runtime="red").get(section, "green")
            if not section == "library":
                edge.set_label(section)
            edge.set_color(color)
            edge.set_fontcolor(color)
            graph.add_edge(edge)
            traverse(child)
    root = pydot.Node(portname)
    traverse(root)
    return graph


if __name__ == '__main__':
    portname = sys.argv[1]
    variants = sys.argv[2:]
    sys.stdout.write(make_tree(portname, variants).to_string())


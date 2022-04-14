# -*- coding: utf-8 -*-
import sys
import os
import unittest

from tempfile import mkdtemp, mkstemp
import shutil
from urllib.error import URLError, HTTPError

import pytest

from rdflib import URIRef, Graph, plugin
from rdflib.exceptions import ParserError
from rdflib.plugin import PluginException
from rdflib.namespace import Namespace, NamespaceManager

from pathlib import Path
from rdflib.store import Store
from rdflib.term import BNode

from test.testutils import GraphHelper
from test.data import tarek, likes, pizza, michel, hates, cheese, bob


def test_property_store() -> None:
    """
    The ``store`` property works correctly.
    """
    graph = Graph()
    assert isinstance(graph.store, Store)

def test_property_identifier_default() -> None:
    """
    The default identifier for a graph is a `rdflib.term.BNode`.
    """
    graph = Graph()
    assert isinstance(graph.identifier, BNode)

def test_property_identifier() -> None:
    """
    The ``identifier`` property works correctly.
    """
    id = URIRef("example:a")
    graph = Graph(identifier=id)
    assert id == graph.identifier

def test_property_namespace_manager() -> None:
    """
    The ``namespace_manager`` property works correctly.
    """
    graph = Graph()
    # check repeats as property is a signleton
    assert isinstance(graph.namespace_manager, NamespaceManager)
    assert isinstance(graph.namespace_manager, NamespaceManager)

    new_nsm = NamespaceManager(graph)
    new_nsm.reset()
    new_nsm.bind("test", URIRef("example:test:"))
    graph.namespace_manager = new_nsm
    assert isinstance(graph.namespace_manager, NamespaceManager)
    nss = list(graph.namespace_manager.namespaces())
    assert ("test", URIRef("example:test:")) in nss


def populate_graph(graph):
    graph.add((tarek, likes, pizza))
    graph.add((tarek, likes, cheese))
    graph.add((michel, likes, pizza))
    graph.add((michel, likes, cheese))
    graph.add((bob, likes, cheese))
    graph.add((bob, hates, pizza))
    graph.add((bob, hates, michel))  # gasp!

def depopulate_graph(graph):
    graph.remove((tarek, likes, pizza))
    graph.remove((tarek, likes, cheese))
    graph.remove((michel, likes, pizza))
    graph.remove((michel, likes, cheese))
    graph.remove((bob, likes, cheese))
    graph.remove((bob, hates, pizza))
    graph.remove((bob, hates, michel))  # gasp!

def test_add():
    graph = Graph()
    populate_graph(graph)

def test_remove():
    graph = Graph()
    populate_graph(graph)
    depopulate_graph(graph)

def test_triples():
    graph = Graph()
    triples = graph.triples
    Any = None

    populate_graph(graph)

    # unbound subjects
    assert len(list(triples((Any, likes, pizza)))) == 2
    assert len(list(triples((Any, hates, pizza)))) == 1
    assert len(list(triples((Any, likes, cheese)))) == 3
    assert len(list(triples((Any, hates, cheese)))) == 0

    # unbound objects
    assert len(list(triples((michel, likes, Any)))) == 2
    assert len(list(triples((tarek, likes, Any)))) == 2
    assert len(list(triples((bob, hates, Any)))) == 2
    assert len(list(triples((bob, likes, Any)))) == 1

    # unbound predicates
    assert len(list(triples((michel, Any, cheese)))) == 1
    assert len(list(triples((tarek, Any, cheese)))) == 1
    assert len(list(triples((bob, Any, pizza)))) == 1
    assert len(list(triples((bob, Any, michel)))) == 1

    # unbound subject, objects
    assert len(list(triples((Any, hates, Any)))) == 2
    assert len(list(triples((Any, likes, Any)))) == 5

    # unbound predicates, objects
    assert len(list(triples((michel, Any, Any)))) == 2
    assert len(list(triples((bob, Any, Any)))) == 3
    assert len(list(triples((tarek, Any, Any)))) == 2

    # unbound subjects, predicates
    assert len(list(triples((Any, Any, pizza)))) == 3
    assert len(list(triples((Any, Any, cheese)))) == 3
    assert len(list(triples((Any, Any, michel)))) == 1

    # all unbound
    assert len(list(triples((Any, Any, Any)))) == 7
    depopulate_graph(graph)
    assert len(list(triples((Any, Any, Any)))) == 0

def test_connected():
    graph = Graph()
    populate_graph(graph)
    assert graph.connected() is True

    jeroen = URIRef("jeroen")
    unconnected = URIRef("unconnected")

    graph.add((jeroen, likes, unconnected))

    assert graph.connected() is False

def test_graph_sub():
    g1 = Graph()
    g2 = Graph()

    g1.add((tarek, likes, pizza))
    g1.add((bob, likes, cheese))

    g2.add((bob, likes, cheese))

    g3 = g1 - g2

    assert len(g3) == 1
    assert (tarek, likes, pizza) in g3
    assert (tarek, likes, cheese) not in g3

    assert (bob, likes, cheese) not in g3

    g1 -= g2

    assert len(g1) == 1
    assert (tarek, likes, pizza) in g1
    assert (tarek, likes, cheese) not in g1

    assert (bob, likes, cheese) not in g1

def test_graph_add():
    g1 = Graph()
    g2 = Graph()

    g1.add((tarek, likes, pizza))
    g2.add((bob, likes, cheese))

    g3 = g1 + g2

    assert len(g3) == 2
    assert (tarek, likes, pizza) in g3
    assert (tarek, likes, cheese) not in g3

    assert (bob, likes, cheese) in g3

    g1 += g2

    assert len(g1) == 2
    assert (tarek, likes, pizza) in g1
    assert (tarek, likes, cheese) not in g1

    assert (bob, likes, cheese) in g1

def test_graph_intersection():
    g1 = Graph()
    g2 = Graph()

    g1.add((tarek, likes, pizza))
    g1.add((michel, likes, cheese))

    g2.add((bob, likes, cheese))
    g2.add((michel, likes, cheese))

    g3 = g1 * g2

    assert len(g3) == 1
    assert (tarek, likes, pizza) not in g3
    assert (tarek, likes, cheese) not in g3

    assert (bob, likes, cheese) not in g3

    assert (michel, likes, cheese) in g3

    g1 *= g2

    assert len(g1) == 1

    assert (tarek, likes, pizza) not in g1
    assert (tarek, likes, cheese) not in g1

    assert (bob, likes, cheese) not in g1

    assert (michel, likes, cheese) in g1

def test_guess_format_for_parse():
    graph = Graph()

    # files
    with pytest.raises(ParserError):
        graph.parse(__file__)  # here we are trying to parse a Python file!!

    # .nt can be parsed by Turtle Parser
    graph.parse("test/nt/anons-01.nt")
    # RDF/XML
    graph.parse("test/rdf/datatypes/test001.rdf")  # XML
    # bad filename but set format
    graph.parse("test/rdf/datatypes/test001.borked", format="xml")

    with pytest.raises(ParserError):
        graph.parse(data="rubbish")

    # Turtle - default
    graph.parse(
        data="<http://example.com/a> <http://example.com/a> <http://example.com/a> ."
    )

    # Turtle - format given
    graph.parse(
        data="<http://example.com/a> <http://example.com/a> <http://example.com/a> .",
        format="turtle",
    )

    # RDF/XML - format given
    rdf = """<rdf:RDF
  xmlns:ns1="http://example.org/#"
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
>
  <rdf:Description rdf:nodeID="ub63bL2C1">
    <ns1:p rdf:resource="http://example.org/q"/>
    <ns1:r rdf:resource="http://example.org/s"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="ub63bL5C1">
    <ns1:r>
      <rdf:Description rdf:nodeID="ub63bL6C11">
        <ns1:s rdf:resource="http://example.org/#t"/>
      </rdf:Description>
    </ns1:r>
    <ns1:p rdf:resource="http://example.org/q"/>
  </rdf:Description>
</rdf:RDF>
    """
    graph.parse(data=rdf, format="xml")

    # URI

    # only getting HTML
    with pytest.raises(PluginException):
        graph.parse(location="https://www.google.com")

    try:
        graph.parse(location="http://www.w3.org/ns/adms.ttl")
        graph.parse(location="http://www.w3.org/ns/adms.rdf")
    except (URLError, HTTPError):
        # this endpoint is currently not available, ignore this test.
        pass

    try:
        # persistent Australian Government online RDF resource without a file-like ending
        graph.parse(
            location="https://linked.data.gov.au/def/agrif?_format=text/turtle"
        )
    except (URLError, HTTPError):
        # this endpoint is currently not available, ignore this test.
        pass

def test_parse_file_uri():
    EG = Namespace("http://example.org/#")
    g = Graph()
    g.parse(Path("./test/nt/simple-04.nt").absolute().as_uri())
    triple_set = GraphHelper.triple_set(g)
    assert triple_set == {
            (EG["Subject"], EG["predicate"], EG["ObjectP"]),
            (EG["Subject"], EG["predicate"], EG["ObjectQ"]),
            (EG["Subject"], EG["predicate"], EG["ObjectR"]),
        }

def test_transitive():
    person = URIRef("ex:person")
    dad = URIRef("ex:dad")
    mom = URIRef("ex:mom")
    mom_of_dad = URIRef("ex:mom_o_dad")
    mom_of_mom = URIRef("ex:mom_o_mom")
    dad_of_dad = URIRef("ex:dad_o_dad")
    dad_of_mom = URIRef("ex:dad_o_mom")

    parent = URIRef("ex:parent")

    g = Graph()
    g.add((person, parent, dad))
    g.add((person, parent, mom))
    g.add((dad, parent, mom_of_dad))
    g.add((dad, parent, dad_of_dad))
    g.add((mom, parent, mom_of_mom))
    g.add((mom, parent, dad_of_mom))

    # transitive parents of person
    assert set(g.transitive_objects(subject=person, predicate=parent)) == {person, dad, mom_of_dad, dad_of_dad, mom, mom_of_mom, dad_of_mom}
    # transitive parents of dad
    assert set(g.transitive_objects(dad, parent)) == {dad, mom_of_dad, dad_of_dad}
    # transitive parents of dad_of_dad
    assert set(g.transitive_objects(dad_of_dad, parent)) == {dad_of_dad}

    # transitive children (inverse of parents) of mom_of_mom
    assert set(g.transitive_subjects(predicate=parent, object=mom_of_mom)) == {mom_of_mom, mom, person}
    # transitive children (inverse of parents) of mom
    assert set(g.transitive_subjects(parent, mom)) == {mom, person}
    # transitive children (inverse of parents) of person
    assert set(g.transitive_subjects(parent, person)) == {person}

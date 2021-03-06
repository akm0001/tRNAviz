from django.test import TestCase, Client, tag, RequestFactory
from django.urls import reverse
import json
from explorer import models
from explorer import services
from explorer import views

@tag('api', 'search')
class SearchTests(TestCase):
  def setUp(self):
    self.client = Client()
    self.factory = RequestFactory()

  def test_nonexistent_clade_query(self):
    request = self.factory.get(reverse('explorer:search', kwargs = {'search_type': 'taxonomy'}), {'term': 'sdcasdf'})
    json_response = services.search(request, 'taxonomy')
    data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(data['results'], [])
  
  def test_valid_lowercase_query(self):
    request = self.factory.get(reverse('explorer:search', kwargs = {'search_type': 'taxonomy'}), {'term': 'japonicus'})
    json_response = services.search(request, 'taxonomy')
    data = json.loads(json_response.content.decode('utf8'))
    self.assertFalse(data['more'])
    self.assertIn({"id": "4897", "text": "Schizosaccharomyces japonicus (species)"}, data['results'])

  def test_assemblies_filtered_query(self):
    request = self.factory.get(reverse('explorer:search', kwargs = {'search_type': 'clade'}), {'term': 'Saccharomyces'})
    json_response = services.search(request, 'clade')
    data = json.loads(json_response.content.decode('utf8'))
    self.assertFalse(data['more'])
    for key in data['results']:
      clade = key['text']
      with self.subTest(clade = clade):
        self.assertFalse('assembly' in clade)

@tag('summary')
class SummaryServicesTests(TestCase):
  def setUp(self):
    self.client = Client()
    self.factory = RequestFactory()
    self.request = self.factory.get('')
    self.clade_txid = '4930'
    self.isotype = 'All'
    self.cloverleaf_cons = models.Consensus.objects.filter(taxid = self.clade_txid, isotype = self.isotype).values()[0]
    self.cloverleaf_near_cons = models.Consensus.objects.filter(taxid = self.clade_txid, isotype = self.isotype).values()[0]
    self.cloverleaf_freqs = services.gather_cloverleaf_freqs(self.clade_txid, self.isotype)
    self.tilemap_cons = models.Consensus.objects.filter(taxid = self.clade_txid).exclude(isotype = 'All').values()
    self.tilemap_freqs = services.gather_tilemap_freqs(clade_txid = self.clade_txid)

  @tag('cloverleaf')
  def test_services_coords(self):
    json_response = self.client.get(reverse('explorer:coords'))
    coords_list = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(coords_list), 95)
    for key in ['x', 'y', 'position', 'radius']:
      with self.subTest(key = key):
        self.assertIn(key, coords_list[0].keys())

  @tag('cloverleaf')
  def test_services_gather_cloverleaf_freqs(self):
    freqs = services.gather_cloverleaf_freqs(self.clade_txid, self.isotype)
    num_positions = len(freqs)
    self.assertEqual(num_positions, 67)
    self.assertEqual(len(freqs['17a']), 5)
    for feature in services.SINGLE_FEATURES:
      with self.subTest(feature = feature):
        self.assertIn(feature, freqs['17a'])
    self.assertEqual(len(freqs['3:70']), 25)
    for feature in services.PAIRED_FEATURES.values():
      with self.subTest(feature = feature):
        self.assertIn(feature, freqs['3:70'])
  
  @tag('cloverleaf')
  def test_services_cloverleaf(self):
    json_response = services.cloverleaf(self.request, self.clade_txid, self.isotype)
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(plot_data), 95)

  @tag('tilemap')
  def test_services_tilemap_gather_freqs(self):
    freqs = services.gather_tilemap_freqs(self.clade_txid)
    for isotype in freqs:
      isotype_freqs = freqs[isotype]
      with self.subTest(isotype = isotype):
        self.assertEqual(len(isotype_freqs), 67)
        self.assertEqual(len(isotype_freqs['17a']), 5)
        self.assertEqual(len(isotype_freqs['3:70']), 25)

  @tag('tilemap')
  def test_services_tilemap(self):
    json_response = services.tilemap(self.request, self.clade_txid)
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(plot_data), 1995) # 21 isotypes * 95 positions

    json_response = services.tilemap(self.request, '5204')
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(plot_data), 1995) # 21 isotypes * 95 positions

    for tile_data in plot_data:
      for key in ['isotype', 'type', 'datatype', 'consensus', 'position', 'freqs']:
        with self.subTest(key = key):
          self.assertIn(key, tile_data)
          if key != 'freqs':
            self.assertEqual(type(tile_data[key]), str)

  @tag('taxonomy-summary')
  def test_taxonomy_summary(self):
    json_response = services.taxonomy_summary(self.request, self.clade_txid, self.isotype)
    counts = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(counts), 9)

    json_response = services.taxonomy_summary(self.request, '7399', self.isotype)
    counts = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(len(counts), 7)

  @tag('domain-features')
  def test_domain_features(self):
    json_response = services.domain_features(self.request, self.clade_txid, self.isotype)
    cons = json.loads(json_response.content.decode('utf8'))
    self.assertIn('position', cons[0])
    self.assertIn('clade', cons[0])
    self.assertIn('domain', cons[0])

  @tag('domain-features')
  def test_domain_features_same_clade(self):
    json_response = services.domain_features(self.request, '2759', self.isotype)
    cons = json.loads(json_response.content.decode('utf8'))
    self.assertIn('position', cons[0])
    self.assertIn('clade', cons[0])
    self.assertIn('domain', cons[0])

  @tag('anticodon-counts')
  def test_anticodon_counts(self):
    response = services.anticodon_counts(self.request, self.clade_txid, self.isotype)
    http = response.content.decode('utf8')
    self.assertIn('Saccharomyces', http)
    self.assertIn('Eukaryota', http)
    self.assertIn('Ala', http)
    self.assertIn('AGC', http)

  @tag('isotype-discrepancies')
  def test_isotype_discrepancies(self):
    response = services.isotype_discrepancies(self.request, self.clade_txid, self.isotype)
    http = response.content.decode('utf8')
    self.assertIn('tRNAscan-SE ID', http)

@tag('api', 'variation', 'distribution')
class DistributionServicesTests(TestCase):
  def setUp(self):
    self.factory = RequestFactory()
    self.request = self.factory.get('')
    self.api_txids = '4930,4895;5204'
    self.api_positions = 'paired,1:72,variable,2:71,8'
    self.api_isotypes = 'His,Met,Phe'
    self.clade_groups = [['4930', '4895'], ['5204']]
    self.num_groups = 2
    self.clade_info = {
      '5204': ('Basidiomycota', 'phylum'), 
      '4895': ('Schizosaccharomyces', 'genus'), 
      '4930': ('Saccharomyces', 'genus')
    }
    self.positions = ['1:72', '2:71', '3:70', '4:69', '5:68', '6:67', '7:66', '8', '10:25', '11:24', '12:23', '13:22', '27:43', '28:42', '29:41', '30:40', '31:39', 'V1', 'V2', 'V3', 'V4', 'V5', 'V11:V21', 'V12:V22', 'V13:V23', 'V14:V24', 'V15:V25', 'V16:V26', 'V17:V27', '49:65', '50:64', '51:63', '52:62', '53:61']
    self.query_positions = ['p1_72', 'p2_71', 'p3_70', 'p4_69', 'p5_68', 'p6_67', 'p7_66', 'p8', 'p10_25', 'p11_24', 'p12_23', 'p13_22', 'p27_43', 'p28_42', 'p29_41', 'p30_40', 'p31_39', 'pV1', 'pV2', 'pV3', 'pV4', 'pV5', 'pV11_V21', 'pV12_V22', 'pV13_V23', 'pV14_V24', 'pV15_V25', 'pV16_V26', 'pV17_V27', 'p49_65', 'p50_64', 'p51_63', 'p52_62', 'p53_61']
    self.query_positions.append('isotype')
    self.isotypes = ['His', 'Met', 'Phe']
    self.trnas = services.query_trnas_for_distribution(self.clade_groups, self.clade_info, self.isotypes, self.query_positions)
    self.freqs = services.convert_trnas_to_freqs_df(self.trnas)
    self.plot_data = services.convert_freqs_to_dict(self.freqs)

  @tag('species')
  def test_services_reconstruct_clade_group_info(self):
    clade_groups, clade_info = services.reconstruct_clade_group_info(self.api_txids)
    self.assertEqual(len(clade_groups), 2)
    self.assertEqual(len(clade_info), 3)
    self.assertEqual(clade_info['5204'], ('Basidiomycota', 'phylum'))

  def test_services_uniquify_positions(self):
    positions = services.uniquify_positions('8,9')
    self.assertEqual(positions, ['8', '9'])
    positions = services.uniquify_positions(self.api_positions)
    self.assertEqual(positions, self.positions)
  
  @tag('species')
  def test_services_query_trnas_for_distribution(self):
    self.assertEqual(len(self.trnas.columns), 36)
    self.assertIn('group', self.trnas.columns)
    self.assertIn('isotype', self.trnas.columns)

  def test_services_convert_trnas_to_freqs_df(self):
    self.assertIn('isotype', self.freqs.columns)
    self.assertIn('group', self.freqs.columns)
    self.assertIn('position', self.freqs.columns)
    self.assertEqual(len(self.freqs.index.levels), 3)
    self.assertEqual(set(self.isotypes), set(self.freqs.index.levels[0]))
    self.assertEqual(set(self.positions), set(self.freqs.index.levels[1]))

  def test_services_convert_freqs_to_dict(self):
    self.assertEqual(len(self.plot_data), len(self.isotypes))
    for isotype in self.isotypes:
      with self.subTest(isotype = isotype):
        self.assertEqual(len(self.plot_data[isotype]), len(self.positions))
        for position in self.positions:
          with self.subTest(position = position):
            self.assertEqual(len(self.plot_data[isotype][position]), self.num_groups)

  def test_services_distribution(self):
    json_response = services.distribution(self.request, self.api_txids, self.api_isotypes, self.api_positions)
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(type(plot_data), dict)
    self.assertTrue(len(plot_data) > 0)

@tag('api', 'variation', 'species')
class SpeciesServicesTests(TestCase):
  def setUp(self):
    self.factory = RequestFactory()
    self.request = self.factory.get('')
    self.api_txids = '4930,4895;5204'
    self.api_foci = '3:70,Gly,All,16.5,100.1;3:70,Asn,All,16.5,70.1'
    self.clade_groups = [['4930', '4895'], ['5204']]
    self.clade_info = {
      '5204': ('Basidiomycota', 'phylum'), 
      '4895': ('Schizosaccharomyces', 'genus'), 
      '4930': ('Saccharomyces', 'genus')
    }
    self.foci = [{'position': '3:70', 'isotype': 'Gly', 'anticodon': 'All', 'score_min': '16.5', 'score_max': '100.1'}, 
      {'position': '3:70', 'isotype': 'Asn', 'anticodon': 'All', 'score_min': '16.5', 'score_max': '70.1'}]
    self.trnas = services.query_trnas_for_species_distribution(self.clade_groups, self.clade_info, self.foci)
    self.freqs = services.species_convert_trnas_to_freqs_df(self.trnas, self.foci)

  def test_services_species_convert_trnas_to_freqs_df(self):
    self.assertIn('focus', self.freqs.columns)
    self.assertIn('group', self.freqs.columns)
    self.assertIn('assembly', self.freqs.columns)
    self.assertIn('isotype', self.freqs.columns)
    self.assertIn('anticodon', self.freqs.columns)
    self.assertIn('score', self.freqs.columns)
    self.assertEqual(self.freqs.index.names, ['focus', 'group', 'assembly'])

  def test_services_species(self):
    json_response = services.species_distribution(self.request, self.api_txids, self.api_foci)
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertEqual(type(plot_data), dict)
    for focus in plot_data:
      for freqs_dict in plot_data[focus]:
        with self.subTest(focus = focus, assembly = freqs_dict['assembly']):
          self.assertEqual(len(freqs_dict), 21)

  def test_services_species_not_enough_trnas(self):
    api_foci = '3:70,Gly,All,160,160.1;3:70,Asn,All,150,151' # no tRNAs exist for either focus
    json_response = services.species_distribution(self.request, self.api_txids, api_foci)
    plot_data = json.loads(json_response.content.decode('utf8'))
    self.assertIn('No tRNAs found.', plot_data['error'])

@tag('taxonomy')
class TaxonomyServicesTests(TestCase):
  def setUp(self):
    self.client = Client()
    self.factory = RequestFactory()
    self.request = self.factory.get('')
    self.taxonomy_id = models.Taxonomy.objects.filter(name = 'Thermoplasmatales')[0].id

  @tag('about')
  def test_genome_summary(self):
    response = services.genome_summary(self.request, 'root')
    http = response.content.decode('utf8')
    self.assertIn('Bacteria', http)
    self.assertIn('Archaea', http)
    self.assertIn('Eukaryota', http)

    response = services.genome_summary(self.request, self.taxonomy_id)
    http = response.content.decode('utf8')
    self.assertIn('Thermoplasmatales', http)
    self.assertIn('Picrophilaceae', http)
    self.assertIn('Thermoplasmatales archaeon BRNA1', http)
    
  def test_score_summary_taxonomy(self):
    response = services.score_summary_taxonomy(self.request, 'root')
    http = response.content.decode('utf8')
    self.assertIn('Bacteria', http)
    self.assertIn('Archaea', http)
    self.assertIn('Eukaryota', http)

    response = services.score_summary_taxonomy(self.request, self.taxonomy_id)
    http = response.content.decode('utf8')
    self.assertIn('Thermoplasmata', http)
    self.assertIn('Picrophilaceae', http)
    self.assertIn('Thermoplasmatales archaeon BRNA1', http)
    
  def test_score_summary_isotype(self):
    response = services.score_summary_isotype(self.request, 'root')
    http = response.content.decode('utf8')
    self.assertIn('Ala', http)
    self.assertIn('AGC', http)
    self.assertIn('Total', http)

  def test_newick_tree(self):
    tree = services.newick_tree(self.taxonomy_id)
    self.assertIn('Picrophilaceae', tree)
    self.assertIn('Thermoplasmata', tree)

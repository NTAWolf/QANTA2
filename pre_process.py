import csv
import cPickle
import os
import datetime as datetime
from nltk.parse import stanford
from config import get_config


def parse_question_csv(csv_path, target_path=None, skip_head=1, sub_delimiter=' ||| ' ):
	"""Builds a list of lists, each of which represents a line in the csv.
	Note that the 5th element in each line is itself a list.

	csv_path is the path to the .csv file on your system
	skip_head is the number of lines to skip in the beginning of the file
	sub_delimiter is the extra delimiter in the 5th column of the file

	If target_path is defined, cPickles the result to that file.
	Otherwise returns the result.
	"""

	csv_questions = []
	with open(csv_path) as f:
		handle = csv.reader(f, strict=True)
		for _ in xrange(skip_head):
			handle.next()

		for i, line in enumerate(handle):
			assert len(line) == 5
			line[4] = line[4].split(sub_delimiter) # Question text
			assert 0 < len(line[4]) < 12, "Error in line {}".format(i + 2)
			csv_questions.append(line)

	with open(target_path, 'wb') as f:
		cPickle.dump(csv_questions, f)

def questions_to_sentences(csv_pickle, sentence_ID_path, sentences_path, question_info_path):
	"""Takes the raw CSV-text as input and outputs each sentence from all the 
	questions. Another list containing the question ID is also outputed."""

	with open(csv_pickle, 'rb') as csvfile:
		csv_questions = cPickle.load(csvfile)

	sentence_ID = []
	sentences = []
	question_information = {}

	for questions in csv_questions:
		question_information[questions[0]] = [questions[1], questions[2], questions[3]]
		for sentence in questions[4]:
			sentences.append(sentence)
			sentence_ID.append(questions[0])

	"""sentence_ID_path = os.path.join(target_path, "sentence_ID")
	sentences_path = os.path.join(target_path, "sentences")
	question_info_path = os.path.join(target_path, "question_info")"""

	with open(sentence_ID_path, 'wb') as f:
		cPickle.dump(sentence_ID, f)

	with open(sentences_path, 'wb') as f:
		cPickle.dump(sentences, f)

	with open(question_info_path, 'wb') as f:
		cPickle.dump(question_information, f)

def node_converter(node, target_path=None):
	"""Convert node to triple:
		address, word, deps
		where deps is a list
			where each element is a tuple
				(dependency_name, [address_dep1, address_dep2, ...])
	"""
	address = node[1]['address']
	word = node[1]['word']
	deps = []
	for k,v in node[1]['deps'].iteritems():
		deps.append((k,v))
	return (address, word, deps)

def dependency_parse(sentences_path, target_path=None):
	"""sentences is a list of strings

	Returns a list, where each element corresponds to the sentence
	in the same index in the input list. The elements are themselves
	lists of tuples: (index_in_sentence, word, dependencies),
	where dependencies are the tuple (dependency_name, [dep1, dep2, ...])
		dep1, dep2 being index_in_sentence for the dependent words
	"""
	with open(sentences_path, 'rb') as sentencesfile:
		sentences = cPickle.load(sentencesfile)

	config = get_config('Stanford Parser')
	# E.g. /usr/local/Cellar/stanford-parser/3.5.2/libexec/stanford-parser.jar
	os.environ['STANFORD_PARSER'] = config['STANFORD_PARSER']
	# E.g. /usr/local/Cellar/stanford-parser/3.5.2/libexec/stanford-parser-3.5.2-models.jar
	os.environ['STANFORD_MODELS'] = config['STANFORD_MODELS']

	parser = stanford.StanfordDependencyParser()
	# We can set java options through java_options. They default to '-mx1000m'

	parsed = parser.raw_parse_sents(sentences)

	output = []
	for sentence in parsed:
		depgraph = list(sentence)
		assert len(depgraph) == 1
		depgraph = depgraph[0]

		root_address = depgraph.root['address']
		nodes = map(node_converter, depgraph.nodes.items())
			
		output.append(nodes)

	return output

def vocabulary(filen, target_path=None):
	"""Takes a file as input, unpickles it and add every entity 
	of it to the vocabulary. Returns vocabulary."""

	with open (filen, 'rb') as f:
		input =  pickle.load(f)

	vocab = {}
	dep_vocab = {}

	for k in range(len(input)):
		for l in range(len(input[k])):
			for m in [0,2]:
				if input[k][l][m][0] in vocab:
					pass
				else:
					print "added " + input[k][l][m][0]
					vocab[input[k][l][m][0]] = len(vocab) + 1
				if input[k][l][1][0] in dep_vocab:
					dep_vocab[[k][l][1][0]] = len(dep_vocab) + 1

	return vocab, dep_vocab

def process(csv_file, output_file, verbosity, process_dir, start_from):

	parsed_csv_path = os.path.join(process_dir, "parsed_csv")
	sentence_ID_path = os.path.join(process_dir, "sentence_ID")
	sentences_path = os.path.join(process_dir, "sentences")
	question_info_path = os.path.join(process_dir, "question_info")

	question_index_path = os.path.join(process_dir, "question_index")
	isolated_questions_path = os.path.join(process_dir, "isolated_questions")
	stanford_parsed_path = os.path.join(process_dir, "stanford_parsed")
	parsed_path = os.path.join(process_dir, "parsed")
	log_path = os.path.join(process_dir, "log")

	if start_from <= 1:
		parse_question_csv(csv_file, parsed_csv_path)
	if start_from <= 2:
		questions_to_sentences(parsed_csv_path, sentence_ID_path, sentences_path, question_info_path)
	if start_from <= 3:
		dependency_parse(sentences_path)

def main():
	import argparse

	# command line arguments
	raw_args = argparse.ArgumentParser(description='QANTA preprocessing: Going from CSV question files to QANTA format')
	raw_args.add_argument('-s', '--source', dest='source_file', help='location of source CSV file',  type=str, default="./his-questions.csv")
	raw_args.add_argument('-o', '--output', dest='output_file', help='location of output file', type=str)
	raw_args.add_argument('-v', '--verbosity', dest='verbosity', 
							help=('Verbosity during processing:'
								  '0: Print nothing.\n'
								  '1: Print when processes end, and where the results are stored.\n'
								  '2: As 1, plus printing whenever a process starts.'), 
							default=2, type=int)
	raw_args.add_argument('-d', '--directory', dest='process_dir', 
							help='Location of directory in which we store stepwise results and log', 
							default=None, type=str)
	raw_args.add_argument('--start-point', dest='start_point', type=int, default=0,
							help=('For starting over from somewhere within the main process. '
								  'If == 0, the full process is run. Otherwise, the number indicates '
								  'where in the the process method we should start. '
								  '(See source code or log file for full reference)'))

	args = raw_args.parse_args()


	if not args.process_dir:
		args.process_dir = 'qanta-preprocess-{}'.format(datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S'))
		pass
	if not os.path.exists(args.process_dir):
		os.makedirs(args.process_dir)
	
	process(csv_file=args.source_file, output_file=args.output_file, 
			verbosity=args.verbosity,  process_dir=args.process_dir, 
			start_from=args.start_point)

if __name__ == '__main__':
	main()
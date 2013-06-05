"""
Provider CSV -> Database CSV
============================

Converts a provider given CSV (which is created with Excel by saving a XLS as CSV) into
a database ready CSV format.

Run without arguments to see usage, or look at usage()

Author: Michael Yoffe       25/04/2012
"""

import logging
import csv
import sys
import re
from datetime import datetime

##################
# Set up logging #
##################

logging.basicConfig(filename='convert.log', level=logging.DEBUG)
log = logging.getLogger()

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)
log.addHandler(stdout_handler)


##############
# Exceptions #
##############

class DataNotFoundError(Exception):
    pass

#############
# Utilities #
#############

def reformat_date(date, source_format, target_format):
    return datetime.strptime(date, source_format).strftime(target_format)

ConverterClasses = []


###########################
# Provider CSV converters #
###########################

class ConverterBase(object):
    """
    Basic template functionality for parsing and converting a
    SIP provider rates CSV into a normalized, preparted for DB insert CSV
    """
    RATE_UNCHANGED = '='                # Rate change indicators
    RATE_INCREASED = '+'
    RATE_DECREASED = '-'

    TARGET_DATE_FORMAT = '%Y%m%d'       # Database date format

    source_date_format = ''             # Date format of original CSV

    source_delimiter = ','              # Delimiter char for input file

    output_delimiter = '|'				# Delimiter char for output file

    def convert(self, in_filename, out_filename):
        """
        Given in_filename CSV, creates a normalized, DB ready
        CSV as out_filename
        """
        lines_written = 0

        with open(in_filename) as in_file, \
             open(out_filename, 'wb') as out_file:
            reader = csv.reader(in_file, dialect='excel', delimiter=self.source_delimiter)
            #writer = csv.writer(out_file)
            writer = csv.writer(out_file, delimiter=self.output_delimiter)
            
            for row in self._data_iterator(reader):
                fixed_row = self._normalized(row)
                writer.writerow(fixed_row)
                lines_written += 1

        log.info('Wrote %d lines to %s', lines_written, out_filename)


    def _data_iterator(self, reader):
        """
        Iterate over only relevant data rows that contain rate information
        """
        found_data = False


        line = 0
        while True:
            # Looking for the beginning of the data
            try:
                row = reader.next()
                line += 1
                if self._is_data_header(row):
                    log.info('Found header at line %d', line)
                    log.debug('Header: %s', row)
                    found_data = True
                    break
                else:
                    log.debug('Skipping line %d: %s', line, row)
            except StopIteration:
                break
            except Exception:
                print 'Error at input line %d' % line
                raise

        if not found_data:
            raise DataNotFoundError()

        # Reading data until its end
        while True:
            try:
                row = reader.next()
                line += 1
                log.debug('Processing line %d: %s', line, row)
                if not self._contains_data(row):
                    log.info('End of data at line %d', line)
                    break

                yield row
            except StopIteration:
                break


    def _normalized(self, row):
        """
        Given an input csv row from a provider CSV file
        build the database ready, normalized, csv row from it.

        Normalized row format:
        <dest>, <prefix>, <usd rate>, <date>, =/+/- (change indicator)

        Example:
            United States-California, 1310, 1.512, 20120102, +
            
            (rate increased)
        """
        out_dest = self._get_destination(row)
        out_prefix = self._get_prefix(row)
        out_rate = self._get_rate(row)
        out_date = self._get_date(row)
        out_changed = self._get_changed(row)

        return out_dest, out_prefix, out_rate, out_date, out_changed


    # Implement in subclass
    def _contains_data(self, row):
        """
        Returns True only if the given csv row has rate data.
        i.e. not header of footer, but the body of the document
        """
        raise NotImplementedError()


    # Implement in subclass
    def _is_data_header(self, row):
        """
        Returns True only if the next line after the given row is the first
        rate data row in the CSV
        """
        raise NotImplementedError()

    # Methods for extrating the output CSV fields from the originial csv row (data)
    # Overriden in concrete, provider-specific converters

    def _get_destination(self, data):
        return data[self.destination_pos]

    def _get_prefix(self, data):
        return data[self.prefix_pos]

    def _get_rate(self, data):
        return data[self.rate_pos]

    def _get_changed(self, data):
        return self.RATE_UNCHANGED
    
    # Optionally override in subclass
    def _normalize_date(self, date):
        return date

    def _get_date(self, data):
        date = data[self.date_pos]
        normal_date = self._normalize_date(date)
        return reformat_date(normal_date, self.source_date_format, self.TARGET_DATE_FORMAT)


class VodafoneConverter(ConverterBase):
    name = 'vodafone'
    source_date_format = '%d-%b-%Y'
    date_pos = 6


    def __init__(self):
        super(VodafoneConverter, self).__init__()


    def _is_data_header(self, row):
        return row[0].lower() == 'country' and row[1].lower() == 'destination'


    def _contains_data(self, row):
        """
        A 'relevant' row is a row that has some data
        """
        return row.count('') < 4


    def _get_destination(self, data):
        return '%s-%s' % (data[0], data[1])

    def _get_prefix(self, data):
        return '%s%s' % (data[3], data[4])

    def _get_rate(self, data):
        gbp = float(data[5])
        return gbp

    def _get_changed(self, data):
        comment = data[8].lower()
        if 'increase' in comment:
            return self.RATE_INCREASED
        elif 'decrease' in comment:
            return self.RATE_DECREASED
        else:
            return self.RATE_UNCHANGED

ConverterClasses.append(VodafoneConverter)


class TmobileConverter(ConverterBase):
    name = 'tmobile'
    source_date_format = '%m/%d/%Y'
    destination_pos = 0
    prefix_pos = 2
    date_pos = 6
    RE_RATE = re.compile('\$\s*(\d+\.\d+)')

    def _is_data_header(self, row):
        return 'destination' in row[0].lower() and 'code' in row[2].lower()


    def _contains_data(self, row):
        """
        A 'relevant' row is a row that has some data
        """
        return row.count('') < 4

    def _get_rate(self, data):
        return self.RE_RATE.search(data[5]).groups(0)[0]

    def _get_changed(self, data):
        comment = data[7].lower()
        if 'increase' in comment:
            return self.RATE_INCREASED
        elif 'decrease' in comment:
            return self.RATE_DECREASED
        else:
            return self.RATE_UNCHANGED

ConverterClasses.append(TmobileConverter)


class SprintConverter(ConverterBase):
    source_delimiter = '\t'
    name = 'sprint'
    destination_pos = 0
    prefix_pos = 1
    date_pos = 5
    rate_pos = 2

    source_date_format = '%b_%d_%Y'
    re_source_date = re.compile('(\w+)\s+(\d+)\s+(\d+)')

    def _is_data_header(self, row):
        return '----' in row[0]

    def _contains_data(self, row):
        return len(row) == 6

    def _get_destination(self, row):
        return row[0]

    def _get_prefix(self, row):
        return row[1]

    def _get_rate(self, row):
        return row[2]

    def _normalize_date(self, date):
        return '_'.join(date.split())

ConverterClasses.append(SprintConverter)

ConverterMap = dict([ (c.name, c) for c in ConverterClasses ])

#########################
######### MAIN ##########
#########################

def usage():
    return """
Usage:
  $ python %s <provider> <infile> <outfile>

  provider:  vodafone | tmobile | sprint
  infile:    provider CSV file to process
  outfile:   result CSV file

Note: The input CSV is created from the provider XLS file by saving it as CSV
""" % sys.argv[0]

def main():
    if len(sys.argv) != 4:
        print usage()
        sys.exit(1)

    converter_arg = sys.argv[1].lower()
    if converter_arg not in ConverterMap.keys():
        print usage()
        sys.exit(1)

    script, provider, infile, outfile = sys.argv

    # Instantiate the converter
    converter = ConverterMap[converter_arg]()

    log.info('Provider:     %s', converter.name)
    log.info('Input file:   %s', infile)
    log.info('Output file:  %s', outfile)
    log.info('')
    log.info('Converting CSV...')

    converter.convert(infile, outfile)

    log.info('Done.')


if __name__ == '__main__':
    main()

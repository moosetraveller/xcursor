"""
xcursor is a generator wrapping an arcpy cursor providing a getter method to
use field names instead of column indices.

Usage:

from xcursor import xcursor

feature_class = "points.shp"
with arcpy.da.SearchCursor(feature_class, ["FieldName"]) as cursor:
    for row in xcursor(cursor):
        print(row["FieldName"]) # instead of row[0]


Copyright (c) 2021 Thomas Zuberbuehler

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import tempfile
import unittest

import arcpy


class XRow():
    """ Wraps an arcpy cursor row. """

    def __init__(self, row, fields):
        self.row = row
        self.fields = fields
        self._fields = {field_name.upper(): index for index, field_name in enumerate(fields)}

    def __getitem__(self, index):
        if isinstance(index, int):
            return self.get_by_index(index)
        return self.get(index)

    def __repr__(self):
        return "xcursor.XRow({}, {})".format(str(self.row), str(self.fields))

    def get(self, field_name, default_value=None):
        """
        Gets the field value for given field.
        In addition to just using ["FieldName"], this method can
        return a default value when the field's value is None.
        """
        if field_name is None or field_name.upper() not in self._fields:
            raise Exception("Field {} does not exist.".format(field_name))
        value = self.row[self._fields[field_name.upper()]]
        if not value:
            return default_value
        return value

    def get_by_index(self, index, default_value=None):
        """
        Gets the field value for given index.
        In addition to just using [index], this method can
        return a default value when the field's value is None.
        """
        if index >= len(self.row):
            raise Exception("Index {} is out of range.".format(index))
        value = self.row[index]
        if not value:
            return default_value
        return value

    def to_dict(self):
        """ Returns a dictionary representation. """
        return {field_name: value for field_name, value in zip(self._fields, self.row)}  # pylint: disable=unnecessary-comprehension


def xcursor(cursor):
    """ Generator wrapping an arcpy cursor providing XRow instances. """
    for row in cursor:
        yield XRow(row, cursor.fields)


class XCursorTest(unittest.TestCase):
    """ Unit test to validate functionality of xcursor. """

    FIELDS = ["Column1", "Column2", "Column3", "Column4"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.temp = None
        self.geodatabase = None
        self.feature_class = None

    def setUp(self):

        self.temp = tempfile.TemporaryDirectory()

        self.geodatabase = arcpy.management.CreateFileGDB(self.temp.name, "test.gdb")
        self.feature_class = arcpy.management.CreateFeatureclass(self.geodatabase, "Test")

        for field in XCursorTest.FIELDS:
            arcpy.management.AddField(self.feature_class, field, "TEXT")

        with arcpy.da.InsertCursor(self.feature_class, XCursorTest.FIELDS) as cursor:
            for index in range(0, 25):
                cursor.insertRow((str(index), "Test", None, "Test {}".format(index)))

    def tearDown(self):

        arcpy.management.ClearWorkspaceCache(self.feature_class)
        arcpy.management.ClearWorkspaceCache(self.geodatabase)

        self.temp.cleanup()

    def test(self):
        """ Tests the xcursor generator. """

        expected_rows = []
        with arcpy.da.SearchCursor(self.feature_class, XCursorTest.FIELDS) as cursor:
            expected_rows = [row for row in cursor][:]

        with arcpy.da.SearchCursor(self.feature_class, XCursorTest.FIELDS) as cursor:

            for index, row in enumerate(xcursor(cursor)):

                expected_row = expected_rows[index]

                for column_index, field in enumerate(XCursorTest.FIELDS):
                    self.assertEqual(row.get(field), expected_row[column_index])
                    self.assertEqual(row[field], expected_row[column_index])
                    self.assertEqual(row.get_by_index(column_index), expected_row[column_index])
                    self.assertEqual(row[column_index], expected_row[column_index])

                self.assertIsNone(row.get("Column3"))
                self.assertEqual("1234", row.get("Column3", "1234"))
                self.assertEqual("1234", row.get_by_index(2, "1234"))


if __name__ == "__main__":
    unittest.main()

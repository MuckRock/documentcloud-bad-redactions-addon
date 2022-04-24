"""
This is an identifying bad redactions add-on for DocumentCloud.
Use the x-ray library, creates annotations where bad redactions exist, and returns the bounding boxes and the text.

It demonstrates how to write a add-on which can be activated from the
DocumentCloud add-on system and run using Github Actions.  It receives data
from DocumentCloud via the request dispatch and writes data back to
DocumentCloud using the standard API
"""

from documentcloud.addon import AddOn
import xray
import csv


class BadRedactions(AddOn):
    """An identifying bad redactions Add-On for DocumentCloud."""

    def main(self):
        """The main add-on functionality goes here."""
        # fetch your add-on specific data
        if not self.documents:
            print("not documents")
            self.set_message("Please select at least one document")
            return

        self.set_message("Identifying Bad Redactions start!")

        # creating a csv file
        with open("bad_redactions.csv", "w+") as file_:
            field_names = ['document_id', 'page_num', 'bbox', 'text']
            writer = csv.DictWriter(file_, fieldnames=field_names)
            writer.writeheader()

            for document in self.client.documents.list(id__in=self.documents):
                # identifying bad redactions using the x-ray library
                bad_redactions = xray.inspect(document.pdf)
                for page in bad_redactions.keys():
                    for i in range(len(bad_redactions[page])):
                        bbox = bad_redactions[page][i]['bbox']
                        writer.writerow({'document_id': document.id,
                                         'page_num': page,
                                         'bbox': bbox,
                                         'text': bad_redactions[page][i]['text']})

                        # creating annotations where bad redactions occur
                        title = "bad redactions"
                        width = 612
                        height = 792
                        document.annotations.create(
                            title, page-1, "bed redactions exist", "private", bbox[0]/width, bbox[1]/height, bbox[2]/width, bbox[3]/height)
            self.upload_file(file_)
        self.set_message("Identidying Bad Redactions end!")


if __name__ == "__main__":
    BadRedactions().main()

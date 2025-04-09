"""
This is an identifying bad redactions add-on for DocumentCloud.
Use the x-ray library, creates annotations where bad redactions exist, 
and returns a csv file including the bounding boxes and the text.
Option to redact bad redactions and delete any existing bad redaction annotations.

It demonstrates how to write a add-on which can be activated from the
DocumentCloud add-on system and run using Github Actions.  It receives data
from DocumentCloud via the request dispatch and writes data back to
DocumentCloud using the standard API
"""
import csv
from documentcloud.addon import AddOn
import xray
from listcrunch import uncrunch


class BadRedactions(AddOn):
    """An identifying bad redactions Add-On for DocumentCloud."""

    def main(self):
        """The main add-on functionality goes here."""
        if self.get_document_count() is None:
            self.set_message("Please select at least one document.")
            return

        self.set_message("Identifying Bad Redactions start!")

        redbadred = self.data.get("fix")

        # creating a csv file
        with open("bad_redactions.csv", "w+", encoding="utf-8") as file_:
            field_names = ["document_id", "page_num", "bbox", "text"]
            writer = csv.DictWriter(file_, fieldnames=field_names)
            writer.writeheader()

            counter = 0
            # to hold the redacttion json dictionary for each individual page in this document
            each_redact = []

            for document in self.get_documents():
                # identifying bad redactions using the x-ray library
                try:
                    bad_redactions = xray.inspect(document.pdf)
                except UnicodeDecodeError:
                    self.send_mail(
                        f"Error processing document {document.canonical_url} with bad redactions",
                        'This document has some kind of formatting issue '
                        'that is preventing it from working with the Add-On. '
                        'Please try compressing the document using'
                        ' the PDF Compression Add-On: ' 
                        'https://www.documentcloud.org/add-ons/MuckRock/compress-pdf-add-on/'
                        ' first. If you are still experiencing issues with running' 
                        ' Bad Redactions on this document after this, please reach out to us' 
                        ' at info@documentcloud.org.'
                    )
                    continue
                finally:
                    self.send_mail(
                        "Error processing document document.canonical_url with bad redactions", 
                        "If you receive this error, please reach out to us at "
                        "info@documentcloud.org with a copy of this email and the "
                        "document you tried to analyze for debugging."
                    )
                    continue

                for page in bad_redactions.keys():
                    # get the page spec from the api
                    dimensions = uncrunch(document.page_spec)
                    # dimensions is now a list of strings
                    dimension = dimensions[page - 1]
                    # dimension is now the dimension of the current page
                    width, height = [float(d) for d in dimension.split("x")]
                    # the dimension is a string "612.0x792.0"
                    # two floats as string separated by a "x"

                    for i in range(len(bad_redactions[page])):
                        counter += 1
                        bbox = bad_redactions[page][i]["bbox"]
                        writer.writerow(
                            {
                                "document_id": document.id,
                                "page_num": page,
                                "bbox": bbox,
                                "text": bad_redactions[page][i]["text"],
                            }
                        )

                        # creating annotations where bad redactions occur
                        title = "Bad redaction detected"

                        # if the redaction is being fixed,
                        # add it to the list of bound boxes for the post request
                        if redbadred:
                            # redact bad redactions
                            # append the specific json dict for this page to global dict
                            each_redact.append(
                                {
                                    "page_number": page - 1,
                                    "x1": bbox[0] / width,
                                    "y1": bbox[1] / height,
                                    "x2": bbox[2] / width,
                                    "y2": bbox[3] / height,
                                }
                            )
                        else:
                            # if not, create an annotation for it
                            document.annotations.create(
                                title,
                                page - 1,
                                bad_redactions[page][i]["text"],
                                "private",
                                bbox[0] / width,
                                bbox[1] / height,
                                bbox[2] / width,
                                bbox[3] / height,
                            )

                if redbadred:
                    # go through and delete any existing bad redaction annotations
                    for annotation in document.annotations:
                        if annotation.title == "Bad redaction detected":
                            annotation.delete()

                if redbadred and each_redact:
                    self.set_message("Redacting Bad Redactions start!")
                    # make the api call for this document
                    self.client.post(
                        f"documents/{document.id}/redactions/", json=each_redact
                    )

            if counter == 0:
                self.set_message("No Bad Redactions Found")
            else:
                self.upload_file(file_)
                self.set_message(str(counter) + " Bad Redactions Found")


if __name__ == "__main__":
    BadRedactions().main()

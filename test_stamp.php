<?php
require_once('/opt/bitnami/php/library/SetaPDF/Autoload.php');

$reader = new SetaPDF_Core_Reader_File('FE_Answers.pdf');

// create a writer
$writer = new SetaPDF_Core_Writer_Http('positioning.pdf', true);
// we create a fresh document instance for demonstration purpose
//$document = new SetaPDF_Core_Document($writer);


$document = SetaPDF_Core_Document::load($reader, $writer);


// create at least one page
$document->getCatalog()->getPages()->create(SetaPDF_Core_PageFormats::A4);

// create a stamper instance
$stamper = new SetaPDF_Stamper($document);

// create a font object
$font = SetaPDF_Core_Font_Standard_Helvetica::create($document);

$stamp_text = "";
if (($handle = fopen("test.csv", "r")) !== FALSE) {
    while (($data = fgetcsv($handle, 1000, ",")) !== FALSE) {
        $num = count($data);
        for ($c=0; $c < $num; $c++) {
		$stamp_text = $stamp_text . " " . $data[$c];
        }
    }
    fclose($handle);
}

// create simple text stamp
$stamp = new SetaPDF_Stamper_Stamp_Text($font, 12);
$stamp->setBorderWidth(1);
$stamp->setPadding(4);
$stamp->setAlign(SetaPDF_Core_Text::ALIGN_CENTER);
$stamp->setText($stamp_text);

// default position: left top
$stamper->addStamp($stamp, array(
    'translateX' => 10,
    'translateY' => -10,
));

// right top
$stamper->addStamp($stamp, array(
    'position' => SetaPDF_Stamper::POSITION_RIGHT_TOP,
    'translateX' => -10,
    'translateY' => -10,
));

// right bottom
$stamper->addStamp($stamp, array(
    'position' => SetaPDF_Stamper::POSITION_RIGHT_BOTTOM,
    'translateX' => -10,
    'translateY' => 10,
));

// left bottom
$stamper->addStamp($stamp, array(
    'position' => SetaPDF_Stamper::POSITION_LEFT_BOTTOM,
    'translateX' => 10,
    'translateY' => 10,
));

// center
$stamper->addStamp($stamp, SetaPDF_Stamper::POSITION_CENTER_MIDDLE);

// stamp the document
$stamper->stamp();

// Show the the while page at a time
$document->getCatalog()->setPageLayout(SetaPDF_Core_Document_PageLayout::SINGLE_PAGE);

/* define a handler with an owner password and without a user
 * password, allow print and copy, and do not encrypt metadata
 */
$secHandler = SetaPDF_Core_SecHandler_Standard_Aes128::factory(
    $document,
    'ITPEC',
    'itpe'
//    SetaPDF_Core_SecHandler::PERM_PRINT | SetaPDF_Core_SecHandler::PERM_COPY,
//    false
);

// Attach the handler to the document
$document->setSecHandler($secHandler);

// add a writer
$document->setWriter(new SetaPDF_Core_Writer_Http('encrypted.pdf', true));

// save and send it to the client
$document->save()->finish();


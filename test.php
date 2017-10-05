<?php
require 'vendor/autoload.php';

// print("simple");

use Aws\S3\S3Client;

$bucket = 'prepbook';
$keyname = 'Datalogue.pdf';
// $filepath should be absolute path to a file on disk						
$filepath = 'D:\';
						
// Instantiate the client.
$s3 = S3Client::factory();

// Upload a file.
$result = $s3->putObject(array(
    'Bucket'       => $bucket,
    'Key'          => $keyname,
    'SourceFile'   => $filepath,
    'ContentType'  => 'text/plain',
    'ACL'          => 'public-read',
    'StorageClass' => 'REDUCED_REDUNDANCY',
    'Metadata'     => array(    
        'param1' => 'value 1',
        'param2' => 'value 2'
    )
));

echo $result['ObjectURL'];
?>

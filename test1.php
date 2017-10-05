<?php
require 'vendor/autoload.php';

use Aws\S3\S3Client;

$bucket = 'prepbook';
$keyname = 'tanat';
						
// Instantiate the client.
$s3 = S3Client::factory();

// Upload data.
$result = $s3->putObject(array(
    'Bucket' => $bucket,
    'Key'    => $keyname,
    'Body'   => 'Hello, world!'
));

echo $result['ObjectURL'];

?>

<?php

require 'vendor/autoload.php';
use Aws\S3\S3Client;
use Aws\Exception\AwsException;

print("hello");

//Create a S3Client
$s3Client = new S3Client([
    'region' => 'ap-southeast-1',
    'version' => '2006-03-01'
]);

print("world");

//Listing all S3 Bucket
$buckets = $s3Client->listBuckets();
//print(len($buckets));
foreach ($buckets['Buckets'] as $bucket){
    echo $bucket['Name']."\n";
}

?>

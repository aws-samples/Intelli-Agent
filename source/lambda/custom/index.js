const AWS = require('aws-sdk');
const fs = require('fs');
const tar = require('tar');

// obsolete for now, use script to upload model.tar.gz to s3 instead
exports.handler = async (event) => {
    const s3 = new AWS.S3();
    const bucketName = process.env.BUCKET_NAME;
    const key = 'model.tar.gz';

    // Create files A and B
    fs.writeFileSync('/tmp/fileA.txt', 'Content of file A');
    fs.writeFileSync('/tmp/fileB.txt', 'Content of file B');

    // Package the files into model.tar.gz
    await tar.c({
        gzip: true,
        file: '/tmp/model.tar.gz',
        cwd: '/tmp',
    }, ['fileA.txt', 'fileB.txt']);

    // Upload model.tar.gz to the S3 bucket
    const fileStream = fs.createReadStream('/tmp/model.tar.gz');
    await s3.upload({
        Bucket: bucketName,
        Key: key,
        Body: fileStream,
    }).promise();

    console.log(`Uploaded model.tar.gz to s3://${bucketName}/${key}`);
};

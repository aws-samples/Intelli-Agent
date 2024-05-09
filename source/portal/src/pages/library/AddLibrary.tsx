import { useContext, useEffect, useState } from 'react';
import { axios } from 'src/utils/request';
import {
  Button,
  Container,
  ContentLayout,
  FileUpload,
  Form,
  FormField,
  Header,
  ProgressBar,
  SpaceBetween,
  StatusIndicator,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import CommonLayout from 'src/layout/CommonLayout';
import ConfigContext from 'src/context/config-context';
import { alertMsg } from 'src/utils/utils';
import { AxiosProgressEvent } from 'axios';

const AddLibrary: React.FC = () => {
  const navigate = useNavigate();
  const config = useContext(ConfigContext);

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const uploadFile = async (file: File) => {
    try {
      setShowProgress(true);
      setShowSuccess(false);
      const resData: any = await axios.post(
        `${config?.apiUrl}/etl/upload-s3-url`,
        {
          file_name: file.name,
          content_type: file.type,
        },
      );
      const uploadPreSignUrl = resData.data.data;
      await axios.put(uploadPreSignUrl, file, {
        headers: {
          'Content-Type': file.type,
        },
        onUploadProgress: (e: AxiosProgressEvent) => {
          const progress = Math.floor((e.loaded * 100) / (e.total ?? 1));
          setUploadProgress(progress);
          if (progress >= 100) {
            setShowProgress(false);
            setUploadFiles([]);
            setShowSuccess(true);
            setUploadProgress(0);
          }
        },
      });
    } catch (error: unknown) {
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  useEffect(() => {
    if (uploadFiles.length > 0) {
      uploadFile(uploadFiles[0]);
    }
  }, [uploadFiles]);

  return (
    <CommonLayout
      activeHref="/library"
      breadCrumbs={[
        {
          text: 'AWS LLM Bot',
          href: '/',
        },
        {
          text: 'Docs Library',
          href: '/library',
        },
        {
          text: 'Add',
          href: '/library/add',
        },
      ]}
    >
      <ContentLayout>
        <Container
          variant="default"
          header={
            <Header
              variant="h2"
              description="Please select the file to be imported"
            >
              Ingest
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="l">
            <Form
              variant="embedded"
              actions={
                <Button
                  loading={showProgress}
                  variant="primary"
                  onClick={() => {
                    navigate('/library');
                  }}
                >
                  Back to list
                </Button>
              }
            >
              <SpaceBetween direction="vertical" size="l">
                <FormField
                  label="Select File"
                  description="After the file is successfully uploaded, the ingestion process will begin."
                >
                  <FileUpload
                    onChange={({ detail }) => setUploadFiles(detail.value)}
                    value={uploadFiles}
                    i18nStrings={{
                      uploadButtonText: (e) =>
                        e ? 'Choose files' : 'Choose file',
                      dropzoneText: (e) =>
                        e ? 'Drop files to upload' : 'Drop file to upload',
                      removeFileAriaLabel: (e) => `Remove file ${e + 1}`,
                      limitShowFewer: 'Show fewer files',
                      limitShowMore: 'Show more files',
                      errorIconAriaLabel: 'Error',
                    }}
                    showFileLastModified
                    showFileSize
                    showFileThumbnail
                    tokenLimit={1}
                    accept=".pdf,.csv,.doc,.docx,.html,.json,.jsonl,.txt,.md"
                    constraintText="Supported file types: pdf, csv, doc, docx, html, json, jsonl, txt, md."
                  />
                </FormField>
                {showProgress && (
                  <FormField>
                    <ProgressBar
                      value={uploadProgress}
                      label="Upload progress"
                    />
                  </FormField>
                )}
                {showSuccess && (
                  <StatusIndicator type="success">
                    Upload Succeed.
                  </StatusIndicator>
                )}
              </SpaceBetween>
            </Form>
          </SpaceBetween>
        </Container>
      </ContentLayout>
    </CommonLayout>
  );
};

export default AddLibrary;

import { useContext, useEffect, useState } from 'react';
import { axios } from 'src/utils/request';
import {
  BreadcrumbGroup,
  Button,
  Container,
  ContentLayout,
  FileUpload,
  FlashbarProps,
  Form,
  FormField,
  Header,
  Input,
  ProgressBar,
  RadioGroup,
  SpaceBetween,
  StatusIndicator,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import CommonLayout from 'src/layout/CommonLayout';
import ConfigContext from 'src/context/config-context';
import {
  IngestResponse,
  CachedDataType,
  BatchOperationStatus,
} from 'src/types';
import { alertMsg } from 'src/utils/utils';
import { AxiosProgressEvent } from 'axios';

const CACHED_PROGRESS_DATA = 'llmbot_cached_progress_knowledge_base_ingest';

let checkStatusInterval: any;

const AddLibrary: React.FC = () => {
  const navigate = useNavigate();
  const config = useContext(ConfigContext);
  const [fileName, setFileName] = useState(
    '华鼎股份：义乌华鼎锦纶股份有限公司关于2024年远期结售汇额度的公告.pdf',
  );
  const [loadingIngest, setLoadingIngest] = useState(false);
  const [flashBar, setFlashBar] = useState<FlashbarProps.MessageDefinition[]>(
    [],
  );
  const [fileEmptyError, setFileEmptyError] = useState(false);
  const [uploadType, setUploadType] = useState('upload');
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
      console.info(uploadPreSignUrl);
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

  const ingestKnowledgeBase = async () => {
    if (!fileName.trim()) {
      setFileEmptyError(true);
      return;
    }
    setLoadingIngest(true);
    const params = {
      s3Bucket: config?.docsS3Bucket,
      s3Prefix: fileName,
      workspaceId: config?.workspaceId,
      offline: 'true',
      qaEnhance: 'false',
      indexType: 'qd',
      operationType: 'create',
    };

    try {
      const result = await axios.post(`${config?.apiUrl}/etl`, params);
      const ingestRes: IngestResponse = result.data;
      setLoadingIngest(false);
      const executionId = ingestRes.execution_id;
      const cachedData: CachedDataType = {
        executionId: executionId,
        fileName: fileName,
      };
      localStorage.setItem(CACHED_PROGRESS_DATA, JSON.stringify(cachedData));
      queryIngestStatus(executionId, fileName);
      checkStatusInterval = setInterval(() => {
        queryIngestStatus(executionId, fileName);
      }, 5000);
    } catch (error: unknown) {
      setLoadingIngest(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  const queryIngestStatus = async (executionId: string, fileName: string) => {
    try {
      const result = await axios.get(`${config?.apiUrl}/etl/status`, {
        params: { executionId: executionId },
      });
      const status: BatchOperationStatus = result.data.execution_status;
      let flashType: FlashbarProps.Type = result.data.execution_status;
      let isLoading = false;
      if (status === BatchOperationStatus.SUCCEEDED) {
        clearInterval(checkStatusInterval);
        flashType = 'success';
      }
      if (status === BatchOperationStatus.FAILED) {
        clearInterval(checkStatusInterval);
        flashType = 'error';
      }
      if (status === BatchOperationStatus.RUNNING) {
        isLoading = true;
        flashType = 'info';
      }
      if (status === BatchOperationStatus.TIMED_OUT) {
        clearInterval(checkStatusInterval);
        flashType = 'error';
      }
      if (status === BatchOperationStatus.ABORTED) {
        flashType = 'error';
      }
      if (status === BatchOperationStatus.PENDING_REDRIVE) {
        isLoading = true;
        flashType = 'error';
      }
      const flashBarItem: FlashbarProps.MessageDefinition = {
        header: status,
        loading: isLoading,
        type: flashType,
        dismissible: true,
        content: `${fileName} ingest is ${status}`,
        id: status,
        onDismiss: () => {
          localStorage.removeItem(CACHED_PROGRESS_DATA);
          setFlashBar([]);
        },
      };
      setFlashBar([flashBarItem]);
    } catch (error: unknown) {
      clearInterval(checkStatusInterval);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  useEffect(() => {
    const cachedData = localStorage.getItem(CACHED_PROGRESS_DATA);
    if (cachedData) {
      const tmpCachedData: CachedDataType = JSON.parse(cachedData);
      queryIngestStatus(tmpCachedData.executionId, tmpCachedData.fileName);
      checkStatusInterval = setInterval(() => {
        queryIngestStatus(tmpCachedData.executionId, tmpCachedData.fileName);
      }, 5000);
    }
    return () => {
      clearInterval(checkStatusInterval);
    };
  }, []);

  return (
    <CommonLayout
      flashBar={flashBar}
      activeHref="/library"
      breadCrumbs={
        <BreadcrumbGroup
          items={[
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
        />
      }
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
                uploadType === 'upload' ? (
                  <Button
                    variant="primary"
                    onClick={() => {
                      navigate('/library');
                    }}
                  >
                    Back to list
                  </Button>
                ) : (
                  <SpaceBetween direction="horizontal" size="xs">
                    <Button
                      formAction="none"
                      variant="link"
                      onClick={() => {
                        navigate(-1);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      loading={loadingIngest}
                      onClick={() => {
                        ingestKnowledgeBase();
                      }}
                    >
                      Ingest
                    </Button>
                  </SpaceBetween>
                )
              }
            >
              <SpaceBetween direction="vertical" size="l">
                <FormField label="Amazon S3 Bucket">
                  <Input value={config?.docsS3Bucket ?? ''} readOnly />
                </FormField>
                <FormField
                  label="Ingest method"
                  description="Please select the ingest method"
                >
                  <RadioGroup
                    onChange={({ detail }) => setUploadType(detail.value)}
                    value={uploadType}
                    items={[
                      { value: 'upload', label: 'Upload File' },
                      { value: 'folder', label: 'Bucket Prefix' },
                    ]}
                  />
                </FormField>
                {uploadType === 'folder' && (
                  <FormField
                    label="Prefix"
                    errorText={
                      fileEmptyError ? 'Please select a file' : undefined
                    }
                  >
                    <Input
                      value={fileName}
                      onChange={({ detail }) => {
                        setFileName(detail.value);
                      }}
                    />
                  </FormField>
                )}
                {uploadType === 'upload' && (
                  <SpaceBetween direction="vertical" size="xs">
                    <FormField
                      label="Upload File"
                      description="After the file is successfully uploaded, the ingestion process will begin."
                      errorText={
                        fileEmptyError ? 'Please select a file' : undefined
                      }
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
                        constraintText="Supported format: .docx, .pdf, .csv, .xls, .xlsx, .txt"
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

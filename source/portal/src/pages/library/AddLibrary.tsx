import { useContext, useEffect, useState } from 'react';
import { axios } from '../../utils/request';
import {
  BreadcrumbGroup,
  Button,
  Container,
  FlashbarProps,
  Form,
  FormField,
  Header,
  Input,
  SpaceBetween,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import CommonLayout from '../../layout/CommonLayout';
import ConfigContext from '../../context/config-context';

const CACHED_PROGRESS_DATA = 'llmbot_cached_progress_knowledge_base_ingest';

let checkStatusInterval: any;

enum BatchOperationStatus {
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  TIMED_OUT = 'TIMED_OUT',
  ABORTED = 'ABORTED',
  PENDING_REDRIVE = 'PENDING_REDRIVE',
}

interface CachedDataType {
  executionId: string;
  fileName: string;
}

interface IngestResponse {
  execution_id: string;
  input_payload: string;
  step_function_arn: string;
}

export default function AddLibrary() {
  const navigate = useNavigate();
  const config = useContext(ConfigContext);
  const [fileName, setFileName] = useState(
    '华鼎股份：义乌华鼎锦纶股份有限公司关于2024年远期结售汇额度的公告.pdf',
  );
  // const [fileList, setFileList] = useState<SelectProps.Option[]>([]);
  // const [file, setFile] = useState<SelectProps.Option | null>(null);
  const [loadingIngest, setLoadingIngest] = useState(false);
  const [flashBar, setFlashBar] = useState<FlashbarProps.MessageDefinition[]>(
    [],
  );
  const [fileEmptyError, setFileEmptyError] = useState(false);

  const listObjects = async () => {
    try {
      const list = axios.get(`${config?.apiUrl}/list`);
      console.info(list);
    } catch (error) {
      console.error(error);
    }
  };

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
    console.info('`${config?.apiUrl}/etl`,:', `${config?.apiUrl}/etl`);
    const result = await axios.post(`${config?.apiUrl}/etl`, params);
    const ingestRes: IngestResponse = result.data;
    console.info('result:', result);

    setLoadingIngest(false);
    const executionId = ingestRes.execution_id;
    const cachedData: CachedDataType = {
      executionId: executionId,
      fileName: fileName,
    };
    localStorage.setItem(CACHED_PROGRESS_DATA, JSON.stringify(cachedData));
    // setFile(null);
    queryIngestStatus(executionId, fileName);
    checkStatusInterval = setInterval(() => {
      queryIngestStatus(executionId, fileName);
    }, 5000);
  };

  const queryIngestStatus = async (executionId: string, fileName: string) => {
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
  };

  useEffect(() => {
    listObjects();
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
            }
          >
            <SpaceBetween direction="vertical" size="l">
              <FormField label="Amazon S3 Bucket">
                <Input value={config?.docsS3Bucket ?? ''} readOnly />
              </FormField>
              <FormField
                label="Documents"
                errorText={fileEmptyError ? 'Please select a file' : undefined}
              >
                {/* <Select
                  disabled
                  filteringType="auto"
                  selectedOption={file}
                  onChange={({ detail }) => {
                    setFileEmptyError(false);
                    setFile(detail.selectedOption);
                  }}
                  options={fileList}
                /> */}
                <Input
                  value={fileName}
                  onChange={({ detail }) => {
                    setFileName(detail.value);
                  }}
                />
              </FormField>
            </SpaceBetween>
          </Form>
        </SpaceBetween>
      </Container>
    </CommonLayout>
  );
}

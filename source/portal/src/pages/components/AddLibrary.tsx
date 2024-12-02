import { useEffect, useState } from 'react';
import { axios } from 'src/utils/request';
import {
  Box,
  Button,
  ExpandableSection,
  FileUpload,
  Form,
  FormField,
  Header,
  Input,
  Modal,
  ProgressBar,
  Select,
  SelectProps,
  SpaceBetween,
  Link,
} from '@cloudscape-design/components';
import { LibraryListItem } from 'src/types';
import { alertMsg, validateNameTagString } from 'src/utils/utils';
import { AxiosProgressEvent } from 'axios';
import { useTranslation } from 'react-i18next';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { ExecutionResponse, PresignedUrlResponse } from 'src/types';
import { DOC_INDEX_TYPE_LIST, RESOURCE_QQ_TEMPLATE } from 'src/utils/const';

interface AddLibraryProps {
  showAddModal: boolean;
  setShowAddModal: (show: boolean) => void;
  reloadLibrary: () => void;
  selectedItem?: LibraryListItem;
  isUpdate?: boolean;
}

const AddLibrary: React.FC<AddLibraryProps> = (props: AddLibraryProps) => {
  const { t } = useTranslation();
  const { showAddModal, setShowAddModal, reloadLibrary } = props;
  const fetchData = useAxiosRequest();
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const [fileEmptyError, setFileEmptyError] = useState(false);

  const [indexName, setIndexName] = useState('');
  const [indexNameError, setIndexNameError] = useState('');
  const [indexType, setIndexType] = useState<SelectProps.Option>(
    DOC_INDEX_TYPE_LIST[0],
  );
  const [tagName, setTagName] = useState('');
  const [tagNameError, setTagNameError] = useState('');
  const [advanceExpand, setAdvanceExpand] = useState(false);
  const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
  const [chatbotOption, setChatbotOption] = useState<SelectProps.Option | null>(
    null,
  );

  useEffect(() => {
    const getExecutionDetails = async () => {
      if (props.isUpdate && props.selectedItem?.executionId) {
        try {
          setIndexName(props.selectedItem?.indexId || '');
          setTagName(props.selectedItem?.tag || '');
          setChatbotOption({
            label: props.selectedItem?.chatbotId.toLowerCase(),
            value: props.selectedItem?.chatbotId.toLowerCase(),
          });
          
          const selectedType = DOC_INDEX_TYPE_LIST.find(
            type => type.value === props.selectedItem?.indexType
          );
          if (selectedType) {
            setIndexType(selectedType);
          }
          setAdvanceExpand(true);
        } catch (error) {
          alertMsg(error instanceof Error ? error.message : String(error), 'error');
        }
      } else {
        setIndexName('');
        setIndexType(DOC_INDEX_TYPE_LIST[0]);
        setTagName('');
        setAdvanceExpand(false);
      }
    };
  
    getExecutionDetails();
  }, [props.isUpdate, props.selectedItem]);

  const executionKnowledgeBase = async (bucket: string, prefix: string) => {

    const baseData = {
      s3Bucket: bucket,
      s3Prefix: prefix,
      offline: 'true',
      qaEnhance: 'false',
      chatbotId: chatbotOption ? chatbotOption.value : 'admin',
      indexId: indexName ? indexName.trim() : undefined,
      indexType: indexType.value,
      tag: tagName ? tagName.trim() : undefined,
    };

    const requestConfig = props.isUpdate ? {
      url: `/knowledge-base/executions/${props.selectedItem?.executionId}`,
      method: 'put' as const,
      data: {
        ...baseData,
        executionId: props.selectedItem?.executionId,
      }
    } : {
      url: `/knowledge-base/executions`,
      method: 'post' as const,
      data: {
        ...baseData,
        operationType: 'create',
      }
    };

    const resExecution: ExecutionResponse = await fetchData(requestConfig);
    
    if (resExecution.execution_id) {
      setIndexName('');
      setTagName('');
    }
  };

  const getChatbotList = async () => {
    try {
      const data = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'get',
      });
      const items: string[] = data.chatbot_ids;
      const getChatbots = items.map((item) => {
        return {
          label: item.toLowerCase(),
          value: item.toLowerCase(),
        };
      });
      setChatbotList(getChatbots);
      setChatbotOption(getChatbots[0]);
    } catch (error: unknown) {
      alertMsg(error instanceof Error ? error.message : String(error), 'error');
    }
  };

  const uploadFilesToS3 = async () => {
    // validate  file
    if (uploadFiles.length <= 0) {
      setFileEmptyError(true);
      return;
    }
    // validate index name
    if (!validateNameTagString(indexName.trim())) {
      setIndexNameError('validation.formatInvalidTagIndex');
      return;
    }
    // validate tag
    if (!validateNameTagString(tagName.trim())) {
      setTagNameError('validation.formatInvalidTagIndex');
      return;
    }
    setShowProgress(true);
    const totalSize = uploadFiles.reduce((acc, file) => acc + file.size, 0);
    let progressMap = new Map();
    let percentage = 0;

    const uploadPromises = uploadFiles.map(async (file) => {
      const resPresignedData: PresignedUrlResponse = await fetchData({
        url: `/knowledge-base/kb-presigned-url`,
        method: 'post',
        data: {
          file_name: file.name,
          content_type: file.type,
        },
      });
      const uploadPreSignUrl = resPresignedData.data;
      return axios.put(uploadPreSignUrl.url, file, {
        headers: {
          'Content-Type': file.type,
        },
        onUploadProgress: (e: AxiosProgressEvent) => {
          progressMap.set(file.name, {
            loaded: e.loaded,
            total: file.size,
          });
          const totalUploaded = Array.from(progressMap.values()).reduce(
            (acc, curr) => acc + curr.loaded,
            0,
          );
          percentage = Math.floor((totalUploaded / totalSize) * 100);
          setUploadProgress(percentage);
          if (percentage >= 100) {
            executionKnowledgeBase(
              uploadPreSignUrl.s3Bucket,
              uploadPreSignUrl.s3Prefix,
            );
          }
        },
      });
    });

    try {
      await Promise.all(uploadPromises);
      if (percentage >= 100) {
        setShowProgress(false);
        setUploadFiles([]);
        setUploadProgress(0);
        alertMsg(t('uploadSuccess'), 'success');
        setShowAddModal(false);
        reloadLibrary();
      }
    } catch (error) {
      console.error('error', error);
      alertMsg(error instanceof Error ? error.message : String(error), 'error');
    }
  };

  useEffect(() => {
    getChatbotList();
  }, []);

  return (
    <Modal
      onDismiss={() => setShowAddModal(false)}
      visible={showAddModal}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              disabled={showProgress}
              variant="link"
              onClick={() => {
                setShowAddModal(false);
              }}
            >
              {t('button.cancel')}
            </Button>
            <Button
              loading={showProgress}
              variant="primary"
              onClick={() => {
                uploadFilesToS3();
              }}
            >
              {t('button.upload')}
            </Button>
          </SpaceBetween>
        </Box>
      }
      header={
        <Header description={t('ingestDesc')}>
          {props.isUpdate ? t('update') : t('ingest')}
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        <Form variant="embedded">
          <SpaceBetween direction="vertical" size="l">
            <FormField
              errorText={fileEmptyError ? t('fileEmptyError') : ''}
              label={t('selectFile')}
              description={t('selectFileDesc')}
            >
              <div className="mt-10">
                <FileUpload
                  onChange={({ detail }) => {
                    setFileEmptyError(false);
                    setUploadFiles(detail.value);
                  }}
                  value={uploadFiles}
                  i18nStrings={{
                    uploadButtonText: (e) =>
                      e ? t('chooseFiles') : t('chooseFile'),
                    dropzoneText: (e) =>
                      e ? t('dropFilesToUpload') : t('dropFileToUpload'),
                    removeFileAriaLabel: (e) => `${t('removeFIle')} ${e + 1}`,
                    limitShowFewer: t('showFewer'),
                    limitShowMore: t('showMore'),
                    errorIconAriaLabel: t('error'),
                  }}
                  multiple={false}
                  showFileLastModified
                  showFileSize
                  accept=".pdf,.csv,.doc,.docx,.html,.json,.txt,.md,.png,.jpg,.jpeg,.webp,.xlsx,.xls"
                  constraintText={`${t('supportFiles')} pdf, csv, docx, html, json, txt, md, png, jpg, jpeg, webp, xlsx, xls.`}
                />
                <div className="mt-5">
                  <Link
                    href={RESOURCE_QQ_TEMPLATE}
                    external
                    externalIconAriaLabel="Opens in a new tab"
                  >
                    {t("downloadQQTemplate")}
                  </Link>
                </div>
              </div>
            </FormField>
            <div>
              <ExpandableSection
                onChange={({ detail }) => {
                  setAdvanceExpand(detail.expanded);
                }}
                expanded={advanceExpand}
                headingTagOverride="h4"
                headerText={t('additionalSettings')}
              >
                <SpaceBetween direction="vertical" size="l">
                  <FormField
                    label={t('chatbotName')}
                    stretch={true}
                  >
                    <Select
                      onChange={({ detail }) => {
                        setChatbotOption(detail.selectedOption);
                      }}
                      selectedOption={chatbotOption}
                      options={chatbotList}
                      placeholder={t('validation.requireChatbot')}
                      empty={t('noChatbotFound')}
                      disabled={props.isUpdate}
                    />
                  </FormField>
                  <FormField
                    label={
                      <>
                        {t('indexName')} -{' '}
                        <Box variant="span" fontWeight="normal">
                          <i>{t('optional')}</i>
                        </Box>
                      </>
                    }
                    stretch={true}
                    errorText={t(indexNameError)}
                  >
                    <Input
                      placeholder="example-index-name"
                      value={indexName}
                      onChange={({ detail }) => {
                        setIndexNameError('');
                        setIndexName(detail.value);
                      }}
                      disabled={props.isUpdate}
                    />
                  </FormField>
                  <FormField label={t('indexType')} stretch={true}>
                    <Select
                      options={DOC_INDEX_TYPE_LIST}
                      selectedOption={indexType}
                      onChange={({ detail }) => {
                        setIndexType(detail.selectedOption);
                      }}
                      disabled={props.isUpdate}
                    />
                  </FormField>
                  <FormField
                    label={
                      <>
                        {t('tag')} -{' '}
                        <Box variant="span" fontWeight="normal">
                          <i>{t('optional')}</i>
                        </Box>
                      </>
                    }
                    stretch={true}
                    errorText={t(tagNameError)}
                  >
                    <Input
                      placeholder="example-tag"
                      value={tagName}
                      onChange={({ detail }) => {
                        setTagNameError('');
                        setTagName(detail.value);
                      }}
                      disabled={props.isUpdate}
                    />
                  </FormField>
                </SpaceBetween>
              </ExpandableSection>
            </div>
            {showProgress && (
              <FormField>
                <ProgressBar
                  value={uploadProgress}
                  label={t('uploadProgress')}
                />
              </FormField>
            )}
          </SpaceBetween>
        </Form>
      </SpaceBetween>
    </Modal>
  );
};

export default AddLibrary;

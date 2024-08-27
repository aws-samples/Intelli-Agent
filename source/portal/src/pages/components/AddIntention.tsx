import { useState } from 'react';
import { format } from 'date-fns';
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
  Link,
  Modal,
  ProgressBar,
  Select,
  SpaceBetween,
} from '@cloudscape-design/components';
import { alertMsg, validateNameTagString } from 'src/utils/utils';
import { AxiosProgressEvent } from 'axios';
import { useTranslation } from 'react-i18next';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { ExecutionResponse, PresignedUrlResponse, SelectedOption } from 'src/types';
import { DEFAULT_EMBEDDING_MODEL } from 'src/utils/const';

interface AddIntentionProps {
  showAddModal: boolean;
  models: SelectedOption[];
  botsOption: SelectedOption[];
  selectedBotOption: SelectedOption | undefined;
  selectedModelOption: SelectedOption | undefined;
  changeBotOption: (option: SelectedOption) => void;
  changeSelectedModel: (option: SelectedOption) => void;
  setShowAddModal: (show: boolean) => void;
  reloadIntention: () => void;
}

const AddIntention: React.FC<AddIntentionProps> = (props: AddIntentionProps) => {
  const { t } = useTranslation();
  const {models, botsOption, selectedModelOption, selectedBotOption, showAddModal, changeBotOption, changeSelectedModel, setShowAddModal, reloadIntention } = props;
  const fetchData = useAxiosRequest();
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const [fileEmptyError, setFileEmptyError] = useState(false);

  const [indexName, setIndexName] = useState('');
  const [indexNameError, setIndexNameError] = useState('');
  const [tagName, setTagName] = useState('');
  const [tagNameError, setTagNameError] = useState('');
  const [advanceExpand, setAdvanceExpand] = useState(false);
  const executionIntention = async (bucket: string, prefix: string) => {
    const resExecution: ExecutionResponse = await fetchData({
      url: `intention/executions`,
      method: 'post',
      data: {
        s3Bucket: bucket,
        s3Prefix: prefix,
        // offline: 'true',
        // qaEnhance: 'false',
        chatbotId: selectedBotOption?.value.toLocaleLowerCase() ?? 'admin',
        index: indexName ? indexName.trim() : undefined,
        model: selectedModelOption?.value ?? DEFAULT_EMBEDDING_MODEL,
        // operationType: 'create',
        tag: tagName ? tagName.trim() : undefined,
      },
    });
    if (resExecution.execution_id) {
      setIndexName('');
      setTagName('');
    }
  };

  const downloadTemplate = async ()=>{
    // setLoadingDownload(true);
    let url:any  = await fetchData({
      url: `intention/download-template`,
      method: 'get',
    });
    startDownload(url);
  }

  const startDownload = (url: string) => {
    const link = document.createElement('a');
    link.href = url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // const downloadTemplate = async (type:string) => {
  //   console.log('download template');
  //   setLoadingDownload(true);
  //   let url:any
  //   if(type==="identifier"){
  //     url = await downloadIdentifierBatchFiles({
  //       filename: `identifier-template-${i18n.language}`,
  //     });
  //   } else {
  //     url = await downloadDataSourceBatchFiles({
  //       filename: `template-${i18n.language}`,
  //     });
  //   }
  //   setLoadingDownload(false);
  //   startDownload(url);
  // };

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
        url: `intention/execution-presigned-url`,
        method: 'post',
        data: {
          timestamp: format(new Date(), 'yyyy-MM-dd HH:mm:ss'),
          file_name: file.name,
          content_type: file.type,
        },
      });
      const uploadPreSignUrlData = resPresignedData.data;
      return axios.put(`${uploadPreSignUrlData.url}`, file, {
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
            executionIntention(
              uploadPreSignUrlData.s3Bucket,
              uploadPreSignUrlData.s3Prefix,
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
        reloadIntention();
      }
    } catch (error) {
      console.error('error', error);
      // setUploadFileError("error")
    }
    setShowProgress(false)
    setUploadFiles([])  
  };

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
      header={<Header description={t('ingestIntentionDesc')}>{t('createIntention')}</Header>}
    >
      
      <SpaceBetween direction="vertical" size="l">
        <Form variant="embedded">
          <SpaceBetween direction="vertical" size="l">
            {/* <div>BOTS: {bots}</div> */}
            <FormField
              errorText={fileEmptyError ? t('fileEmptyError') : ''}
              label={t('selectFile')}
              description={<>{t('selectFileDesc')}<Link href="#" variant="info" onFollow={downloadTemplate}>下载模版</Link></>}
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
                  accept=".xlsx"
                  constraintText={`${t('supportFiles')} xlsx.`}
                  // errorText={uploadFileError}
                />
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
                  <FormField label={t('bot')} stretch={true}>
                    <Select
                      options={botsOption}
                      selectedOption={selectedBotOption||{}}
                      onChange={({ detail }:{detail: any}) => {
                        changeBotOption(detail.selectedOption);
                      }}
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
                    />
                  </FormField>
                  <FormField label={t('model')} stretch={true}>
                    <Select
                      options={models}
                      selectedOption={selectedModelOption||{}}
                      onChange={({ detail }:{detail: any}) => {
                        changeSelectedModel(detail.selectedOption);
                      }}
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

export default AddIntention;

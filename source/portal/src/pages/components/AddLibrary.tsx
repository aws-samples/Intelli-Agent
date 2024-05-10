import { useContext, useState } from 'react';
import { axios } from 'src/utils/request';
import {
  Box,
  Button,
  FileUpload,
  Form,
  FormField,
  Header,
  Modal,
  ProgressBar,
  SpaceBetween,
} from '@cloudscape-design/components';
import ConfigContext from 'src/context/config-context';
import { alertMsg } from 'src/utils/utils';
import { AxiosProgressEvent } from 'axios';
import { useTranslation } from 'react-i18next';

interface AddLibraryProps {
  showAddModal: boolean;
  setShowAddModal: (show: boolean) => void;
  reloadLibrary: () => void;
}

const AddLibrary: React.FC<AddLibraryProps> = (props: AddLibraryProps) => {
  const config = useContext(ConfigContext);
  const { t } = useTranslation();
  const { showAddModal, setShowAddModal, reloadLibrary } = props;

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const [fileEmptyError, setFileEmptyError] = useState(false);

  const uploadFilesToS3 = async () => {
    if (uploadFiles.length <= 0) {
      setFileEmptyError(true);
      return;
    }
    setShowProgress(true);
    const totalSize = uploadFiles.reduce((acc, file) => acc + file.size, 0);
    let progressMap = new Map();
    let percentage = 0;

    const uploadPromises = uploadFiles.map(async (file) => {
      const resData: any = await axios.post(
        `${config?.apiUrl}/etl/upload-s3-url`,
        {
          file_name: file.name,
          content_type: file.type,
        },
      );
      const uploadPreSignUrl = resData.data.data;
      console.info('uploadPreSignUrl:', uploadPreSignUrl);
      return axios.put(uploadPreSignUrl, file, {
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
    }
  };

  return (
    <Modal
      onDismiss={() => setShowAddModal(false)}
      visible={showAddModal}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
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
      header={<Header description={t('ingestDesc')}>{t('ingest')}</Header>}
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
                  multiple
                  showFileLastModified
                  showFileSize
                  accept=".pdf,.csv,.doc,.docx,.html,.json,.jsonl,.txt,.md"
                  constraintText={`${t('supportFiles')} pdf, csv, doc, docx, html, json, jsonl, txt, md.`}
                />
              </div>
            </FormField>
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

import React, { useCallback, useContext, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  BreadcrumbGroup,
  Button,
  ContentLayout,
  Header,
  Modal,
  SpaceBetween,
  StatusIndicator,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import ConfigContext from 'src/context/config-context';
import { axios } from 'src/utils/request';
import { LibraryListItem, LibraryListResponse } from 'src/types';
import { alertMsg } from 'src/utils/utils';
import TableLink from 'src/comps/link/TableLink';

const Library: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<LibraryListItem[]>([]);
  const [visible, setVisible] = useState(false);
  const navigate = useNavigate();
  const config = useContext(ConfigContext);
  const [loadingData, setLoadingData] = useState(false);
  const [libraryList, setLibraryList] = useState<LibraryListItem[]>([]);
  const [loadingDelete, setLoadingDelete] = useState(false);

  const getLibraryList = async () => {
    setLoadingData(true);
    const params = {
      size: 9999,
      total: 9999,
    };
    try {
      const result = await axios.get(`${config?.apiUrl}/etl/list-execution`, {
        params,
      });
      const items: LibraryListResponse = result.data;
      setLibraryList(items.Items);
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  const removeLibrary = async () => {
    try {
      setLoadingDelete(true);
      const result = await axios.post(
        `${config?.apiUrl}/etl/delete-execution`,
        {
          executionId: selectedItems.map((item) => item.executionId),
        },
      );
      setVisible(false);
      getLibraryList();
      alertMsg(result.data.message, 'success');
      setLoadingDelete(false);
    } catch (error: unknown) {
      setLoadingDelete(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  useEffect(() => {
    getLibraryList();
  }, []);

  const renderStatus = (status: string) => {
    if (status === 'COMPLETED') {
      return <StatusIndicator type="success">Completed</StatusIndicator>;
    } else if (status === 'IN-PROGRESS') {
      return <StatusIndicator type="loading">In Progress</StatusIndicator>;
    } else {
      return <StatusIndicator type="error">Failed</StatusIndicator>;
    }
  };

  const LinkComp = useCallback(
    (item: LibraryListItem) => (
      <TableLink
        url={`/library/detail/${item.executionId}`}
        name={item.executionId}
      />
    ),
    [],
  );

  return (
    <CommonLayout
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
          ]}
        />
      }
    >
      <ContentLayout>
        <Table
          resizableColumns
          loading={loadingData}
          onSelectionChange={({ detail }) =>
            setSelectedItems(detail.selectedItems)
          }
          selectedItems={selectedItems}
          ariaLabels={{
            selectionGroupLabel: 'Items selection',
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${
                selectedItems.length === 1 ? 'item' : 'items'
              } selected`,
          }}
          columnDefinitions={[
            {
              id: 'executionId',
              header: 'ID',
              cell: (item: LibraryListItem) => LinkComp(item),
              sortingField: 'name',
              isRowHeader: true,
            },
            {
              id: 'bucket',
              header: 'Bucket',
              cell: (item: LibraryListItem) => item.s3Bucket,
              sortingField: 'alt',
            },
            {
              id: 'prefix',
              header: 'Prefix',
              cell: (item: LibraryListItem) => item.s3Prefix,
            },
            {
              width: 150,
              id: 'offline',
              header: 'Offline',
              cell: (item: LibraryListItem) => item.offline,
            },
            {
              width: 150,
              id: 'qaEnhance',
              header: 'QA Enhance',
              cell: (item: LibraryListItem) => item.qaEnhance,
            },
            {
              width: 150,
              id: 'indexType',
              header: 'Index Type',
              cell: (item: LibraryListItem) => item.indexType,
            },
            {
              width: 160,
              id: 'status',
              header: 'Status',
              cell: (item: LibraryListItem) =>
                renderStatus(item.executionStatus),
            },
          ]}
          items={libraryList}
          loadingText="Loading resources"
          selectionType="multi"
          trackBy="executionId"
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
              <SpaceBetween size="m">
                <b>No resources</b>
                <Button>Create resource</Button>
              </SpaceBetween>
            </Box>
          }
          filter={
            <TextFilter
              filteringPlaceholder="Find resources"
              filteringText=""
            />
          }
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    disabled={selectedItems.length <= 0}
                    onClick={() => {
                      setVisible(true);
                    }}
                  >
                    Delete
                  </Button>
                  <Button
                    variant="primary"
                    onClick={() => {
                      navigate('/library/add');
                    }}
                  >
                    Create Docs Library
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${libraryList.length})`
                  : `(${libraryList.length})`
              }
            >
              Documents Library
            </Header>
          }
        />
        <Modal
          onDismiss={() => setVisible(false)}
          visible={visible}
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => {
                    setVisible(false);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  loading={loadingDelete}
                  variant="primary"
                  onClick={() => {
                    removeLibrary();
                  }}
                >
                  Delete
                </Button>
              </SpaceBetween>
            </Box>
          }
          header="Delete"
        >
          Are you sure you want to delete the selected items ?
          <div className="selected-items-list">
            <ul>
              {selectedItems.map((item) => (
                <li key={item.executionId}>{item.executionId}</li>
              ))}
            </ul>
          </div>
        </Modal>
      </ContentLayout>
    </CommonLayout>
  );
};

export default Library;

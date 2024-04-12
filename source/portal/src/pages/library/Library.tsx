import React from 'react';
import CommonLayout from '../../layout/CommonLayout';
import {
  Box,
  BreadcrumbGroup,
  Button,
  CollectionPreferences,
  Header,
  Link,
  Pagination,
  SpaceBetween,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';

const Library: React.FC = () => {
  const [selectedItems, setSelectedItems] = React.useState([
    {
      name: 'Item 1',
      alt: 'First',
      description: 'This is the first item',
      type: '1A',
      size: 'Small',
    },
  ]);
  const navigate = useNavigate();
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
      <Table
        variant="full-page"
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
            id: 'variable',
            header: 'Variable name',
            cell: (item) => <Link href="#">{item.name}</Link>,
            sortingField: 'name',
            isRowHeader: true,
          },
          {
            id: 'value',
            header: 'Text value',
            cell: (item) => item.alt,
            sortingField: 'alt',
          },
          {
            id: 'type',
            header: 'Type',
            cell: (item) => item.type,
          },
          {
            id: 'description',
            header: 'Description',
            cell: (item) => item.description,
          },
        ]}
        columnDisplay={[
          { id: 'variable', visible: true },
          { id: 'value', visible: true },
          { id: 'type', visible: true },
          { id: 'description', visible: true },
        ]}
        enableKeyboardNavigation
        items={[
          {
            name: 'Item 1',
            alt: 'First',
            description: 'This is the first item',
            type: '1A',
            size: 'Small',
          },
          {
            name: 'Item 2',
            alt: 'Second',
            description: 'This is the second item',
            type: '1B',
            size: 'Large',
          },
          {
            name: 'Item 3',
            alt: 'Third',
            description: '-',
            type: '1A',
            size: 'Large',
          },
          {
            name: 'Item 4',
            alt: 'Fourth',
            description: 'This is the fourth item',
            type: '2A',
            size: 'Small',
          },
          {
            name: 'Item 5',
            alt: '-',
            description: 'This is the fifth item with a longer description',
            type: '2A',
            size: 'Large',
          },
          {
            name: 'Item 6',
            alt: 'Sixth',
            description: 'This is the sixth item',
            type: '1A',
            size: 'Small',
          },
        ]}
        loadingText="Loading resources"
        selectionType="multi"
        trackBy="name"
        empty={
          <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
            <SpaceBetween size="m">
              <b>No resources</b>
              <Button>Create resource</Button>
            </SpaceBetween>
          </Box>
        }
        filter={
          <TextFilter filteringPlaceholder="Find resources" filteringText="" />
        }
        header={
          <Header
            actions={
              <SpaceBetween direction="horizontal" size="xs">
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
                ? '(' + selectedItems.length + '/10)'
                : '(10)'
            }
          >
            Documents Library
          </Header>
        }
        pagination={<Pagination currentPageIndex={1} pagesCount={2} />}
        preferences={
          <CollectionPreferences
            title="Preferences"
            confirmLabel="Confirm"
            cancelLabel="Cancel"
            preferences={{
              pageSize: 10,
              contentDisplay: [
                { id: 'variable', visible: true },
                { id: 'value', visible: true },
                { id: 'type', visible: true },
                { id: 'description', visible: true },
              ],
            }}
            pageSizePreference={{
              title: 'Page size',
              options: [
                { value: 10, label: '10 resources' },
                { value: 20, label: '20 resources' },
              ],
            }}
            wrapLinesPreference={{}}
            stripedRowsPreference={{}}
            contentDensityPreference={{}}
            contentDisplayPreference={{
              options: [
                {
                  id: 'variable',
                  label: 'Variable name',
                  alwaysVisible: true,
                },
                { id: 'value', label: 'Text value' },
                { id: 'type', label: 'Type' },
                { id: 'description', label: 'Description' },
              ],
            }}
            stickyColumnsPreference={{
              firstColumns: {
                title: 'Stick first column(s)',
                description:
                  'Keep the first column(s) visible while horizontally scrolling the table content.',
                options: [
                  { label: 'None', value: 0 },
                  { label: 'First column', value: 1 },
                  { label: 'First two columns', value: 2 },
                ],
              },
              lastColumns: {
                title: 'Stick last column',
                description:
                  'Keep the last column visible while horizontally scrolling the table content.',
                options: [
                  { label: 'None', value: 0 },
                  { label: 'Last column', value: 1 },
                ],
              },
            }}
          />
        }
      />
    </CommonLayout>
  );
};

export default Library;

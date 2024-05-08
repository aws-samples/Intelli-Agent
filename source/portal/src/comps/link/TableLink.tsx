import { Link } from '@cloudscape-design/components';
import React from 'react';

interface TableLinkProps {
  name: string;
  url: string;
}

const TableLink: React.FC<TableLinkProps> = (props: TableLinkProps) => {
  const { name, url } = props;
  return <Link href={`${url}`}>{name}</Link>;
};

export default TableLink;

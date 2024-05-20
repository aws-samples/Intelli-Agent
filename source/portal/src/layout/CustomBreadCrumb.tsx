import { BreadcrumbGroup } from '@cloudscape-design/components';
import React from 'react';
import { useNavigate } from 'react-router-dom';

export type BreadCrumbType = {
  text: string;
  href: string;
};

export interface ICustomBreadCrumbProps {
  breadcrumbItems: BreadCrumbType[];
}

const CustomBreadCrumb: React.FC<ICustomBreadCrumbProps> = (
  props: ICustomBreadCrumbProps,
) => {
  const { breadcrumbItems } = props;
  const navigate = useNavigate();
  return (
    <BreadcrumbGroup
      items={breadcrumbItems}
      expandAriaLabel="Show path"
      ariaLabel="Breadcrumbs"
      onFollow={(e) => {
        e.preventDefault();
        navigate(e.detail.href);
      }}
    />
  );
};

export default CustomBreadCrumb;

import { Input, Select } from '@cloudscape-design/components';
import './style.scss';
import { useContext } from 'react';
// import ConfigContext from 'context/config-context';
import { useTranslation } from 'react-i18next';
import ConfigContext from 'src/context/config-context';
interface OIDCProps {
    provider: any,
    username: string,
    password: string,
    oidcOptions: any[],
    setProvider: Function,
    setUsername: Function,
    setPassword: Function,
    setSelectedProviderName: Function,
    setError: Function
}
const OIDC = (props: OIDCProps) => {
    const { t } = useTranslation();
    const {provider,
           username,
           password,
           oidcOptions,
           setProvider,
           setUsername,
           setPassword,
           setSelectedProviderName,
           setError
           } = props;
    
    return (
      <div className='oidc'>
        <div className='item'>
          <Select
            placeholder={t('auth:chooseOIDC').toString()}
            selectedOption={provider}
            onChange={({ detail }:{detail: any}) => {
               setError('')
               setProvider(detail.selectedOption)
               setSelectedProviderName(detail.selectedOption.value)
              }
            }
            options={oidcOptions}
          />
        </div>
        <div className='item'>
          <Input
            onChange={({ detail }) => {
              setError('');
              setUsername(detail.value)}
            }
            value={username}
            placeholder={t('auth:inputUsername').toString()}
          />
        </div>
        <div className='item'>
          <Input
            type='password'
            onChange={({ detail }) => {
              setError('');
              setPassword(detail.value)}
            }
            value={password}
            placeholder={t('auth:inputPassword').toString()}
          />
        </div>    
    </div>)
}

export default OIDC
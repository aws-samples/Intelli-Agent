import { Grid, Input } from '@cloudscape-design/components';
import './style.scss';
import React from 'react';
interface SNSProps{
   username:string
   password: string
   setUsername: (username:string)=>void
   setPassword: (username:string)=>void
}
const SNS = (props: SNSProps) => {
    const {username, password, setUsername, setPassword} = props
    return (<div className='user'>
        
    {/* </Grid> */}
    {/* <Grid
      gridDefinition={[{ colspan: 3 }, { colspan: 9 }]}
    >
        <div className='label'>Username</div> */}
        <div className='item'>
        <Input
      onChange={({ detail }) => setUsername(detail.value)}
      value={username}
      placeholder="Please input phone no."
    />
        </div>
        <Grid gridDefinition={[{ colspan: 7},{ colspan: 5}]}>
        <div className='item'>
        <Input
        type='password'
      onChange={({ detail }) => setPassword(detail.value)}
      value={password}
      placeholder="Please input sns code"
    />
        </div><div className='item' style={{height:'100%'}}>
          <div style={{height:"calc(100% - 18px)", width:"100%" ,border:"1px solid rgba(128, 128, 128, 0.3803921569)" ,display:'flex', alignItems:'center',justifyContent:'center',borderRadius:5, background:'rgba(128, 128, 128, 0.38)'}}>
          GET SNS CODE
          </div>
        
        </div>
        </Grid>
    {/* </Grid>    */}
    
    
    </div>)
}

export default SNS
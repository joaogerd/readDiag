!-----------------------------------------------------------------------------!
!           Group on Data Assimilation Development - GDAD/CPTEC/INPE          !
!-----------------------------------------------------------------------------!
!BOI
!
! ! TITLE: GSI Diagnostic Tool Documentation \\ Version 1.0.0
!
! !AUTHORS: Jo\~a Gerd Z. de Mattos
!
! !AFFILIATION: Group on Data Assimilation Development, CPTEC/INPE, Cachoeira Paulista - SP
! 
! !DATE: May 15, 2012
!
! !INTRODUCTION: Package Overview
!
!    ReadDiagMod is a Fortran 90 collection of routines/functions for 
!    read and get all informations inside GSI diagnostic files.
!    
!EOI
!---------------------------------------------------------------------
!BOP
!---------------------------------------------------------------------
! !ROUTINE: ReadDiagMod.f90
!---------------------------------------------------------------------
!               INPE/CPTEC Data Assimilation Group                   
!---------------------------------------------------------------------
!
! !REVISION HISTORY:
!  15 May 2012 - J. G. de Mattos - Initial Version
!  14 Aug 2017 - J. G. de Mattos - change to modular version
!  09 Oct 2017 - J. G. de Mattos - Include characteristics of OOP
!  19 Oct 2017 - J. G. de Mattos - Modify to read radiation diag file
!
!---------------------------------------------------------------------
!


module ReadDiagModRad
  implicit none
  private
  
  public :: Diag
!  public :: ObsInfo
!  public :: ObsType
!  public :: node

  !
  ! Some parameters
  !
  Real,    Parameter :: udef  = 1.e15  ! Undefined Value
  Logical, Parameter :: noiqc = .true. ! Logical Flag to OI QC (See GSI Manual)

 
  !
  ! Parameters
  !
  
  integer, parameter  :: StrLen   = 512
  integer, parameter  :: i_kind   = selected_int_kind(8)
  integer, parameter  :: r_single = selected_real_kind(6)

  !
  ! Diagnostic derived types
  !

  type :: Diag
     Private
     type(SatInfo),   pointer :: arq => null()
     integer, public, pointer :: nObs => null()
     contains
        procedure, public :: Open        => Open_
!        procedure, public :: Close       => Close_
!        procedure, public :: CalcStat    => CalcStat_
!        procedure, public :: PrintCount  => PrintCountStat_
!        procedure, public :: GetTotalObs => GetTotalObs_
!        procedure, public :: GetNObs     => GetNObs_
!        procedure, public :: GetObsInfo  => GetObsInfo_
!        procedure, public :: GetFirstVar => GetFirstVar_
!        procedure, public :: Gobt => GObt_
  end type

  type :: SatInfo

     character(20)   :: isis    ! sensor/instrument/satellite id  ex.amsua_n15
     character(10)   :: dplat   ! satellite (platform) id
     character(10)   :: obstype ! type of tb observation

     ! Count data of different surface type 
     integer         :: nobs    ! total observations
     integer         :: sea     ! observations over sea/water
     integer         :: land    ! observation over land
     integer         :: ice     ! observation over ice
     integer         :: snow    ! observation over snow
     integer         :: mixed   ! observations over mixed surface

     integer(i_kind) :: nchanl  ! number of channels per obs (written on diag only with iuse_rad >= 1)
     integer(i_kind) :: npred   ! number of radiance biases predictors
     integer(i_kind) :: idate   ! analysis date in YYYYMMDDHH variable

     type(ChanInfo), pointer  :: Channel => null()
     type(ChanInfo), pointer  :: ChannelHead => null()

     integer, allocatable    :: use  (:)  ! total # of used observation
     integer, allocatable    :: nuse (:)  ! total # of unused observation
     integer, allocatable    :: rej  (:)  ! total # of rejeited observation by GSI Quality Control
     integer, allocatable    :: mon  (:)  ! total # of monitored observation
     real,    allocatable    :: vies (:)  ! bias
     real,    allocatable    :: rmse (:)  ! root mean square error
     real,    allocatable    :: mean (:)  ! mean 
     real,    allocatable    :: std  (:)

     type(RadData), pointer  :: data => null()
     type(RadData), pointer  :: DataHead => null()

  end type SatInfo

  type :: ChanInfo
     real :: freq   ! Frequency
     real :: pol    ! Polarization
     real :: wave   ! WaveNumber
     real :: varch  ! variance for clear radiance
     real :: tlap   ! mean lapse rate (fixed from input file)
     real :: iuse   ! use to turn off satellite radiance data
     real :: nuchan ! satellite channel
     real :: ich
     type(ChanInfo), pointer :: next => null()
  end type ChanInfo


  type :: RadData

     real :: lat    ! observation latitude (degrees)
     real :: lon    ! observation longitude (degrees)
     real :: zsges  ! model (guess) elevation at observation location 
     real :: dtime  ! observation time (hours relative to analysis time)
     real :: iscanp ! sensor scan position 
     real :: zasat  ! satellite zenith angle (degrees)
     real :: ilazi  ! satellite azimuth angle (degrees)
     real :: pangs  ! solar zenith angle (degrees)
     real :: isazi  ! solar azimuth angle (degrees)
     real :: sgagl  ! sun glint angle (degrees) (sgagl)
 
     real :: sfcwc  ! fractional coverage by water
     real :: sfclc  ! fractional coverage by land
     real :: sfcic  ! fractional coverage by ice
     real :: sfcsc  ! fractional coverage by snow
     real :: sfcwt  ! surface temperature over water (K)
     real :: sfclt  ! surface temperature over land (K)
     real :: sfcit  ! surface temperature over ice (K)
     real :: sfcst  ! surface temperature over snow (K)
     real :: sfcstp ! soil temperature (K)
     real :: sfcsmc ! soil moisture
     real :: sfcltp ! surface land type
     real :: sfcvf  ! vegetation fraction
     real :: sfcsd  ! snow depth
     real :: sfcws  ! surface wind speed (m/s)

     ! if microwave
     real, pointer :: cls => null()   ! cloud fraction (%)
     real, pointer :: cldp => null()  ! cloud top pressure (hPa)
     ! else
     real, pointer :: clw => null()   ! cloud liquid water (kg/m**2)
     real, pointer :: tpwc => null()  ! total column precip. water (km/m**2)

     ! Informations by channel
     type(RadDataChannel), pointer :: ChannelData => null()
     type(RadDataChannel), pointer :: ChannelDataHead => null()
     
     ! Next data
     type(RadData), pointer :: Next => null()
  
  end type RadData

  type :: RadDataChannel

     real :: tb_obs ! observed brightness temperature (K)
     real :: tbc    ! observed - simulated Tb with bias corrrection (K)
     real :: tbcnob ! observed - simulated Tb with no bias correction (K)
     real :: errinv ! inverse observation error
     real :: idqc   ! quality control mark or event indicator
     real :: emiss  ! surface emissivity
     real :: tlach  ! stability index
     real :: ts     ! d(Tb)/d(Ts)
     real, allocatable :: predterms(:) ! Tb bias correction terms (K)

     ! extra info
     real, pointer :: weigthmax => null()  ! press. at max of weighting fn (mb)
     real, pointer :: tb_obs_sdv => null() ! observed BT standard deviation within averaging box

     type(RadDataChannel), pointer :: Next => null()

  end type RadDataChannel
  
!EOP
!--------------------------------------------------------------------!
contains
!--------------------------------------------------------------------!
!BOP
! 
! !FUNCTION: Open_()
!
! !DESCRIPTION: Função utilizada para abrir os arquivos diagnóticos
!               das observações convencionais do GSI e carregar
!               a informação na estrutura de dados ObsInfo
!
! !INTERFACE:
  function Open_(self, FileNameMask) result(iret)
     use m_string, only: str_template
     class(Diag)                     :: self
!
! !INPUT PARAMETERS:
!
     Character(len=*), intent(in   ) :: FileNameMask ! Nome do arquivo a ser lido
                                                     ! use a palavra chave %e no nome 
                                                     ! do arquivo para ler diretamente
                                                     ! os diversos arquivos escritos
                                                     ! por cada processo MPI do GSI 
!
! !OUTPUT PARAMETERS:
!
     Integer                         :: iret ! Código de erro
                                             !   0 : Sem erro
                                             !  -1 : File not found
                                             ! -99 : Erro na leitura
!EOP
!--------------------------------------------------------------------!
!EOC
     !
     ! local var
     !

     character(len=StrLen)    :: FileName
     type(SatInfo),  pointer  :: info => null()
     type(ChanInfo), pointer  :: Channel =>  null()
     type(RadData),  pointer  :: rad => null()


     integer :: ios
     integer :: ipe
     integer :: lu
     integer :: i, j
     integer :: count
     character(len=15)                           :: MyName

     logical                                     :: isNewVar
     logical                                     :: existe


     !
     ! Informations from file header
     ! Gerenal Info
     character(20)   :: isis    ! sensor/instrument/satellite id  ex.amsua_n15
     character(10)   :: dplat   ! satellite (platform) id
     character(10)   :: obstype ! type of tb observation
     integer(i_kind) :: jiter   ! outer iteration counter
     integer(i_kind) :: nchanl  ! number of channels per obs (written on diag only with iuse_rad >= 1)
     integer(i_kind) :: npred   ! number of radiance biases predictors
     integer(i_kind) :: idate   ! analysis date in YYYYMMDDHH variable
     integer(i_kind) :: ireal   ! number of real entries per spot in radiance
     integer(i_kind) :: ipchan  ! number of entries per channel per spot in radiance diagnostic file
     integer(i_kind) :: iextra  ! number of extra pieces of information to write to diagnostic file
     integer(i_kind) :: jextra  ! number of extra pieces of information to write to diagnostic file

     ! Chanel info
     real(r_single)  :: freq4    ! Frequency
     real(r_single)  :: pol4     ! Polarization
     real(r_single)  :: wave4    ! WaveNumber
     real(r_single)  :: varch4   ! variance for clear radiance
     real(r_single)  :: tlap4    ! mean lapse rate (fixed from input file)
     integer(i_kind) :: iuse_rad ! use to turn off satellite radiance data
!                                        = -2 do not use
!                                        = -1 monitor if diagnostics produced
!                                        =  0 monitor and use in QC only
!                                        =  1 use data with complete quality control
!                                        =  2 use data with no airmass bias correction
!                                        =  3 use data with no angle dependent bias correction
!                                        =  4 use data with no bias correction
     integer(i_kind) :: nuchan   ! satellite channel
     integer(i_kind) :: ich
     
     logical            :: microwave
     logical, parameter :: lwrite_peakwt = .false. ! logical to write out approximate peak pressure of weighting

     !
     ! Diagnostics matrix
     !
     real(r_single),allocatable,dimension( : ) :: diagbuf     ! diagnostics
     real(r_single),allocatable,dimension(:,:) :: diagbufex   ! extra diagnostics by channel
     real(r_single),allocatable,dimension(:,:) :: diagbufchan ! channel information

     logical :: sea, land, ice, snow, mixed

     print*,'1'
     info => self%arq
     print*,'2'

     lu  = 100
     ipe = 0
     count = 0
!     OpenFiles: do
        write(MyName,'(I4.4)')ipe
        FileName = trim(FileNameMask)
        call str_template(strg=FileName,label=MyName)
        inquire(File=trim(Filename), exist=existe)

        if( ipe .eq. 0 .and. .not. existe)then
           write(*,'(A,1x,A)')'File not found:',trim(FileName)
           iret = -1
           return
        endif
        print*,'OpenFile',trim(FileName)
        OPEN ( UNIT   = lu,            &
               FILE   = trim(FileName),&
               STATUS = 'OLD',         &
               IOSTAT = ios,           &
               CONVERT= 'BIG_ENDIAN',  &
               ACCESS = 'SEQUENTIAL',  &
               FORM   = 'UNFORMATTED')
        if(ios.ne.0) then
           return
!          count = count + 1
!          if (count <= 10 )then
!             cycle
!          else
             ! se não existirem 10 arquivos na sequencia
             ! sai do processo
!             exit
!          endif
        endif

        if ( ipe == 0 )then
           read(lu) isis, dplat, obstype, jiter, nchanl, npred, idate, ireal, ipchan, iextra, jextra

!           if (isEmpty(info)) then

              allocate(info)
              info%nobs    = 0
              info%sea     = 0
              info%land    = 0
              info%ice     = 0
              info%snow    = 0
              info%mixed   = 0
              info%isis    = isis
              info%dplat   = dplat
              info%obstype = obstype
              info%nchanl  = nchanl
              info%npred   = npred
              info%idate   = idate

              allocate(info%Channel)
              Channel => info%Channel
              info%ChannelHead => Channel

              allocate(info%data)
              rad => info%data
              info%DataHead => rad
           
!           endif

           microwave = ( trim(obstype) == 'amsua' .or. &
                         trim(obstype) == 'amsub' .or. &
                         trim(obstype) ==   'mhs' .or. &
                         trim(obstype) ==   'msu' .or. &
                         trim(obstype) ==   'hsb' .or. &
                         trim(obstype) ==  'ssmi' .or. &
                         trim(obstype) == 'ssmis' .or. &
                         trim(obstype) == 'amsre' .or. &
                         trim(obstype) ==  'atms'      &
                       )


           do i = 1, nchanl
              read(lu) freq4, pol4, wave4, varch4, tlap4,iuse_rad, nuchan, ich

              if(.not.associated(Channel)) allocate(Channel)

              Channel%freq   = freq4
              Channel%pol    = pol4
              Channel%wave   = wave4
              Channel%varch  = varch4
              Channel%tlap   = tlap4
              Channel%iuse   = iuse_rad
              Channel%nuchan = nuchan
              Channel%ich    = ich

              Channel => Channel%next
           end do

        endif

        allocate(diagbuf(ireal))
        allocate(diagbufchan(ipchan+npred+1,nchanl))
        if(iextra > 0) allocate(diagbufex(iextra,jextra))

        ReadSatData: do 
           if(.not.associated(rad)) allocate(rad)
           if ( iextra > 0 )then
              read(lu, err=997,end=110)diagbuf, diagbufchan, diagbufex
           else
              read(lu, err=997,end=110)diagbuf, diagbufchan
           endif

           rad%lat    = diagbuf( 1)     ! observation latitude (degrees)
           rad%lon    = diagbuf( 2)     ! observation longitude (degrees)
           rad%zsges  = diagbuf( 3)     ! model (guess) elevation at observation location 
           rad%dtime  = diagbuf( 4)     ! observation time (hours relative to analysis time)
           rad%iscanp = diagbuf( 5)     ! sensor scan position 
           rad%zasat  = diagbuf( 6)     ! satellite zenith angle (degrees)
           rad%ilazi  = diagbuf( 7)     ! satellite azimuth angle (degrees)
           rad%pangs  = diagbuf( 8)     ! solar zenith angle (degrees)
           rad%isazi  = diagbuf( 9)     ! solar azimuth angle (degrees)
           rad%sgagl  = diagbuf(10)     ! sun glint angle (degrees) (sgagl)
 
           rad%sfcwc  = diagbuf(11)     ! fractional coverage by water
           rad%sfclc  = diagbuf(12)     ! fractional coverage by land
           rad%sfcic  = diagbuf(13)     ! fractional coverage by ice
           rad%sfcsc  = diagbuf(14)     ! fractional coverage by snow

           !
           ! Count data of different surface types
           !

           if (rad%sfcwc >= 0.99)then
              info%sea = info%sea + 1
           else if(rad%sfclc >= 0.99)then
              info%land = info%land + 1
           else if(rad%sfcic >= 0.99)then
              info%ice = info%ice + 1
           else if(rad%sfcsc >= 0.99)then
              info%snow = info%snow + 1
           else
              info%mixed = info%mixed + 1
           endif

           rad%sfcwt  = diagbuf(15)     ! surface temperature over water (K)
           rad%sfclt  = diagbuf(16)     ! surface temperature over land (K)
           rad%sfcit  = diagbuf(17)     ! surface temperature over ice (K)
           rad%sfcst  = diagbuf(18)     ! surface temperature over snow (K)
           rad%sfcstp = diagbuf(19)     ! soil temperature (K)
           rad%sfcsmc = diagbuf(20)     ! soil moisture
           rad%sfcltp = diagbuf(21)     ! surface land type
           rad%sfcvf  = diagbuf(22)     ! vegetation fraction
           rad%sfcsd  = diagbuf(23)     ! snow depth
           rad%sfcws  = diagbuf(24)     ! surface wind speed (m/s)

           if ( microwave )then
              allocate(rad%cls, rad%cldp)
              rad%cls  = diagbuf(25)    ! cloud fraction (%)
              rad%cldp = diagbuf(26)    ! cloud top pressure (hPa)
           else
              allocate(rad%clw, rad%tpwc)
              rad%clw  = diagbuf(25)    ! cloud liquid water (kg/m**2)
              rad%tpwc = diagbuf(26)    ! total column precip. water (km/m**2)
           endif
           
           !
           ! Get data by channel
           ! like a vertical profile
           !
           allocate(rad%ChannelData)
           rad%ChannelDataHead => rad%ChannelData

           if (lwrite_peakwt)then

              rad%ChannelData => rad%ChannelDataHead
              do i = 1, nchanl
                 if(.not.associated(rad%ChannelData))allocate(rad%ChannelData)
                 rad%ChannelData%weigthmax = diagbufex(1,i)
                 rad%ChannelData => rad%ChannelData%Next
              enddo

              if(trim(obstype) == 'goes_img')then
                 rad%ChannelData => rad%ChannelDataHead
                 do i = 1, nchanl
                    rad%ChannelData%tb_obs_sdv = diagbufex(2,i)
                    rad%ChannelData => rad%ChannelData%Next
                 enddo
              endif

           else if (trim(obstype) == 'goes_img' .and. .not. lwrite_peakwt)then
              rad%ChannelData => rad%ChannelDataHead
              do i = 1, nchanl
                 if(.not.associated(rad%ChannelData))allocate(rad%ChannelData)
                 rad%ChannelData%tb_obs_sdv = diagbufex(1,i)
                 rad%ChannelData => rad%ChannelData%Next
              enddo
           endif

           rad%ChannelData => rad%ChannelDataHead
           do i = 1, nchanl
              if(.not.associated(rad%ChannelData))allocate(rad%ChannelData)

              rad%channelData%tb_obs = diagbufchan(1,i)   ! observed brightness temperature (K)
              rad%channelData%tbc    = diagbufchan(2,i)   ! observed - simulated Tb with bias corrrection (K)
              rad%channelData%tbcnob = diagbufchan(3,i)   ! observed - simulated Tb with no bias correction (K)
              rad%channelData%errinv = diagbufchan(4,i)   ! inverse observation error
              rad%channelData%idqc   = diagbufchan(5,i)   ! quality control mark or event indicator
              rad%channelData%emiss  = diagbufchan(6,i)   ! surface emissivity
              rad%channelData%tlach  = diagbufchan(7,i)   ! stability index
              rad%channelData%ts     = diagbufchan(8,i)   ! d(Tb)/d(Ts)

              allocate(rad%channelData%predterms(npred+2))
              do j = 1, npred + 2
                 rad%channelData%predterms(j) = diagbufchan(ipchan+j,i) ! Tb bias correction terms (K)
              enddo

              rad%ChannelData => rad%ChannelData%Next
           enddo

           !-----------------------------------------------!
           ! Some statistics counts

           ! - total observations
           info%nobs = info%nobs + 1

           ! - Count data of different surface types
           if (rad%sfcwc >= 0.99)then
              info%sea = info%sea + 1
           else if(rad%sfclc >= 0.99)then
              info%land = info%land + 1
           else if(rad%sfcic >= 0.99)then
              info%ice = info%ice + 1
           else if(rad%sfcsc >= 0.99)then
              info%snow = info%snow + 1
           else
              info%mixed = info%mixed + 1
           endif
          
           !-----------------------------------------------!

           rad => rad%next

        enddo ReadSatData
110     continue

        deallocate(diagbuf)
        deallocate(diagbufchan)

        close(lu)
!        ipe = ipe + 1

!     enddo OpenFiles

     self%arq => info
     print*,info%nobs
!     print*,info%sea+info%land+info%ice+info%snow+info%mixed

     print*,info%land, info%ice, info%mixed
!     self%nobs = info%nobs
  
     iret = 0
     return

997  iret = -95
     return
  end function

!  function close_(self) result(iret)
!     class(Diag) :: self
!     integer     :: iret
!
!     type(ObsInfo), pointer :: Obs => null()
!     type(ObsType), pointer :: kx => null()
!     type(node),    pointer :: ObsData => null()
!
!     iret = 0
!
!     Obs => self%arq%FirstVar%NextVar
!     do
!
!        kx => self%arq%FirstVar%OT%next
!        do
!
!           ObsData => self%arq%FirstVar%OT%head%next
!           do
!              deallocate(self%arq%FirstVar%OT%head)
!              if(.not.associated(ObsData)) exit
!              self%arq%FirstVar%OT%head => ObsData
!              ObsData => ObsData%next
!           enddo
!
!           deallocate(self%arq%FirstVar%OT)
!           if(.not.associated(kx)) exit
!           self%arq%FirstVar%OT => kx
!           kx => self%arq%FirstVar%OT%next
!
!        enddo
!
!        deallocate(self%arq%FirstVar)
!        if(.not.associated(Obs)) exit
!        self%arq%FirstVar => Obs
!        Obs => self%arq%FirstVar%NextVar
!     enddo
!
!  end function


 end module ReadDiagModRad

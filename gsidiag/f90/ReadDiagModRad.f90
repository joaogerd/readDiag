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
!    .
!    .
!    .
!    .
!
!
!    +----------+------------+
!    | Variable |    Units   |
!    +----------+------------+
!    |    t     |     K      |
!    |    q     |   kg/kg    |
!    |    ps    |    hPa     |
!    |    uv    |    m/s     |
!    |    gps   |            |
!    |    sst   |     K      |
!    +----------+------------+
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
!
!
!---------------------------------------------------------------------
!


module ReadDiagModRad
  implicit none
  private
  
  public :: rDiag
  public :: ObsInfo
  public :: SatPlat

  !
  ! Parameters
  !
  
  integer, parameter  :: StrLen = 512
  integer, parameter  :: i_kind = selected_int_kind(8)
  integer, parameter  :: r_kind = selected_real_kind(6)

  !
  ! Some parameters
  !
  Logical,      parameter :: noiqc = .true. ! Logical Flag to OI QC (See GSI Manual)
  
  Real(r_kind), parameter :: udef  = -1.0e15_r_kind ! Undefined Value
  real(r_kind), parameter :: r10   = 10.0_r_kind
  real(r_kind), parameter :: zero  =  0.0_r_kind
  real(r_kind), parameter :: one   =  1.0_r_kind
  real(r_kind), parameter :: rtiny = r10 * tiny(zero)
  !
  ! Levels to be Analyzed.
  ! These levels will be analyzed by layers
  !
  ! ex. 1000.00 - 1200.0
  !      900.00 -  999.9
  !        .         . 
  !        .         .
  !        .         .
  !        0.00 - 2000.0 this level will contain information about all levels
  !


  integer, parameter :: nlev = 14
  real, public, dimension(nlev), target :: default_levs = [       &
       1000.0,&
       900.0,&
       800.0,&
       700.0,&
       600.0,&
       500.0,&
       400.0,&
       300.0,&
       250.0,&
       200.0,&
       150.0,&
       100.0,&
       50.0,&
       0.0  &
       ]

  !
  ! radiation diagnostic derived types
  !
  !
  !    rDiag
  !      ├── nType
  !      ├── nObs
  !      ├── maxChanl
  !      ├── oInfo
  !      │      ├── sensor
  !      │      ├── nChanl
  !      │      ├── date
  !      │      ├── nSatID
  !      │      ├── Used
  !      │      ├── nUsed
  !      │      ├── imp
  !      │      ├── dfs
  !      │      ├── oSat
  !      │      │     ├── idplat
  !      │      │     ├── nObs
  !      │      │     ├── Used
  !      │      │     ├── nUsed
  !      │      │     ├── imp
  !      │      │     ├── dfs
  !      │      │     ├── oData
  !      │      │     │     ├── obsType
  !      │      │     │     ├── idplat
  !      │      │     │     ├── nChanl
  !      │      │     │     ├── lat
  !      │      │     │     ├── lon
  !      │      │     │     ├── elev
  !      │      │     │     ├── time
  !      │      │     .     .
  !      │      │     .     .
  !      │      │     .     .
  !      │      │     
  !      │      │     │     ├── imp
  !      │      │     │     ├── dfs
  !      │      │     .     .
  !      │      │     .     .
  !      │      │     .     .
  !      │      │     .     .
  !      │      │     │     ├── chInfo
  !      │      │     │     │     ├── freq
  !      │      │     │     │     ├── pol
  !      │      │     │     │     ├── wave
  !      │      │     │     │     ├── varCh
  !      │      │     │     │     ├── tlap
  !      │      │     │     │     ├── iuse
  !      │      │     │     │     ├── nuChan
  !      │      │     │     │     └── ich
  !      │      │     │     └── chData
  !      │      │     │           ├── tb_obs
  !      │      │     │           ├── omf
  !      │      │     │           ├── omf_nobc
  !      │      │     │           ├── oer
  !      │      │     │           ├── errinv
  !      │      │     │           ├── idqc
  !      │      │     │           ├── emiss
  !      │      │     │           ├── tlach
  !      │      │     │           ├── ts
  !      │      │     │           ├── oma
  !      │      │     │           ├── oma_nobc
  !      │      │     │           ├── imp
  !      │      │     │           ├── dfs
  !      │      │     │           ├── weigthmax
  !      │      │     │           └── tb_obs_sdv
  !      │      │     │
  !      │      │     │
  !      │      │     . 
  !      │      │     . 
  !      │      │     . 
  !      │      │     
  !      │      │     ├── next(oData)
  !      │      │     .
  !      │      .     .
  !      │      .     .
  !      │      .
  !      │      
  !      │      ├── next(oSat)
  !      │      .
  !      .      .
  !      .      .
  !      .      
  !            
  !      ├── next(oInfo)
  !
  !-------------------------------------------------------------------------
  type :: rDiag
     Private
     type(ObsInfo), pointer         :: oInfo => null()
     integer, public, pointer       :: nType => null()
     integer, public, pointer       :: nObs  => null()
     integer, public, pointer       :: MaxChanl => null()
     logical, public                        :: impact
     real(r_kind), public           :: udef
     contains
!        procedure,   public  :: Open        => Open_
        generic,   public  :: Open        => Open_, Open__
        procedure, private :: Open_, Open__
        procedure, public  :: Close       => Close_
        procedure, public  :: CalcStat    => CalcStat_
        procedure, public  :: GetImpact   => GetImpact_
        procedure, public  :: Sumarize    => Sumarize_
!        procedure, public  :: PrintCount  => PrintCountStat_
        procedure, public  :: GetTotalObs => GetTotalObs_
        procedure, public  :: GetNObs     => GetNObs_
        procedure, public  :: GetDate     => GetDate_
        procedure, public  :: GetObsInfo  => GetObsInfo_
        procedure, public  :: GetFirstSensor => GetFirstSensor_
        procedure, public  :: Gobt        => GObt_
        procedure, public  :: GetSensors  => GetSensors_
        procedure, public  :: getSensorInfo => getSensorInfo_
        procedure, public  :: getSatPlataform => getSatPlataform_
!        procedure, public  :: testecount  => testeCount__
  end type

  type :: ObsInfo ! this is the head observational info
!     private
     character(len=10)       :: Sensor
     integer                 :: nChanl
     integer                 :: date        ! YYYYMMDDHH
     integer                 :: ymd         ! Year/month/Day
     integer                 :: hms         ! hour/minute/second
     integer                 :: nobs        ! total # of observation
     integer                 :: nSatID      ! # of sattelite plataforms
     integer                 :: Used
     integer                 :: noUsed
     logical                 :: stats = .false.
     logical                 :: impact= .false.

     real,    allocatable    :: imp  (:)  ! observation impact
     real,    allocatable    :: dfs  (:)  ! degree of freedom for signal

     type(SatPlat), pointer  :: oSat  => null() 

     ! ObsInfo list
     type(ObsInfo), pointer  :: First => null()
     type(ObsInfo), pointer  :: Next  => null()
  end type ObsInfo


  type :: SatPlat
     character(len=10)      :: idplat
     integer                :: nobs
     integer                :: used
     integer                :: noused
     real, allocatable      :: imp(:)
     real, allocatable      :: dfs(:)
     type(RadData), pointer :: oData => null()

     ! Satellite Plataform Id list
     type(SatPlat), pointer :: First => null()
     type(SatPlat), pointer :: Next  => null()
  end type SatPlat

  type :: RadData
     ! Identification
     character(len=10)   :: obstype ! type of tb observation (KX - são os sensores - semelhante ao kx)
     character(len=10)   :: idplat  ! satellite (platform) id
     integer             :: nchanl  ! number of channels

     ! Location
     real                :: lat    ! observation latitude (degrees)
     real                :: lon    ! observation longitude (degrees)
     real                :: elev   ! model (guess) elevation at observation location
     real                :: time   ! obs time (minutes relative to analysis time)

     ! sensor/sat info
     real                :: iscanp ! sensor scan position 
     real                :: zasat  ! satellite zenith angle (degrees)
     real                :: ilazi  ! satellite azimuth angle (degrees)
     real                :: pangs  ! solar zenith angle (degrees)
     real                :: isazi  ! solar azimuth angle (degrees)
     real                :: sgagl  ! sun glint angle (degrees) (sgagl)
   
     ! surface parameters
     real                :: sfcwc  ! fractional coverage by water
     real                :: sfclc  ! fractional coverage by land
     real                :: sfcic  ! fractional coverage by ice
     real                :: sfcsc  ! fractional coverage by snow
     
     real                :: sfcwt  ! surface temperature over water (K)
     real                :: sfclt  ! surface temperature over land (K)
     real                :: sfcit  ! surface temperature over ice (K)
     real                :: sfcst  ! surface temperature over snow (K)
     real                :: sfcstp ! soil temperature (K)
     real                :: sfcsmc ! soil moisture
     real                :: sfcltp ! surface land type
     real                :: sfcvf  ! vegetation fraction
     real                :: sfcsd  ! snow depth
     real                :: sfcws  ! surface wind speed (m/s)

     real, pointer       :: imp => null() ! total observation impact 
     real, pointer       :: dfs => null() ! total degree of freedom for signal  

     ! if microwave
     real, pointer       :: cls => null()   ! cloud fraction (%)
     real, pointer       :: cldp => null()  ! cloud top pressure (hPa)
     ! else
     real, pointer       :: clw => null()   ! cloud liquid water (kg/m**2)
     real, pointer       :: tpwc => null()  ! total column precip. water (km/m**2)

     ! Informations by channel
     type(ChannelInfo), pointer :: chInfo(:) => null()
     type(ChannelData), pointer :: chData(:) => null()
     
     ! Radiance data list
     type(RadData), pointer :: First => null()
     type(RadData), pointer :: Next => null()

  end type

  type :: ChannelInfo
     real :: freq   ! Frequency
     real :: pol    ! Polarization
     real :: wave   ! WaveNumber
     real :: varch  ! variance for clear radiance
     real :: tlap   ! mean lapse rate (fixed from input file)
     real :: iuse   ! use to turn off satellite radiance data
     real :: nuchan ! satellite channel
     real :: ich
  end type ChannelInfo

  type :: ChannelData

     real :: tb_obs   ! observed brightness temperature (K)
     real :: omf      ! observed - simulated Tb with bias corrrection (K)
     real :: omf_nobc ! observed - simulated Tb with no bias correction (K)
     real :: oer      ! observation error
     real :: errinv  ! inverse observation error
     real :: idqc    ! quality control mark or event indicator
     real :: emiss   ! surface emissivity
     real :: tlach   ! stability index
     real :: ts      ! d(Tb)/d(Ts)
     
     real, allocatable :: predterms(:) ! Tb bias correction terms (K)

     ! Analisys info 
     real, pointer :: oma      => null() ! observed - simulated Tb with bias corrrection (K)
     real, pointer :: oma_nobc => null() ! observed - simulated Tb with no bias correction (K)
     real, pointer :: imp      => null() ! observation impact
     real, pointer :: dfs      => null() ! degree of freedom for signal

     ! extra info
     real, pointer :: weigthmax => null()  ! press. at max of weighting fn (mb)
     real, pointer :: tb_obs_sdv => null() ! observed BT standard deviation within averaging box

  end type ChannelData




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
  function Open_(self, FileNameMask, IsisList) result(iret)
     use m_string, only: str_template
     class(rDiag)                     :: self
!
! !INPUT PARAMETERS:
!
     Character(len=*),           intent(in   ) :: FileNameMask ! Nome do arquivo a ser lido
                                                               ! use a palavra chave %e no nome 
                                                               ! do arquivo para ler diretamente
                                                               ! os diversos arquivos escritos
                                                               ! por cada processo MPI do GSI 
                                                               
     Character(len=*), optional, intent(in   ) :: IsisList(:)  ! lista com o nome dos satélites/sensores
                                                               ! a serem lidos
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

     character(len=StrLen)  :: FileName
     type(ObsInfo), pointer :: info => null()

     integer :: ios
     integer :: lu
     integer :: i, j
     integer :: nFiles, iFile
     character(len=15)      :: myName
     logical                :: isNewType
     logical                :: existe




    !
     ! Informations from file header
     ! Gerenal Info
     character(20)   :: isis    ! sensor/instrument/satellite id  ex.amsua_n15
     character(10)   :: dplat   ! satellite (platform) id (ex. n15)
     character(10)   :: obstype ! type of tb observation (ex. amsua)
     integer(i_kind) :: jiter   ! outer iteration counter
     integer(i_kind) :: nchanl  ! number of channels per obs (written on diag only with iuse_rad >= 1)
     integer(i_kind) :: npred   ! number of radiance biases predictors
     integer(i_kind) :: idate   ! analysis date in YYYYMMDDHH variable
     integer(i_kind) :: ireal   ! number of real entries per spot in radiance
     integer(i_kind) :: ipchan  ! number of entries per channel per spot in radiance diagnostic file
     integer(i_kind) :: iextra  ! number of extra pieces of information to write to diagnostic file
     integer(i_kind) :: jextra  ! number of extra pieces of information to write to diagnostic file

     ! Chanel info
     real(r_kind)  :: freq4    ! Frequency
     real(r_kind)  :: pol4     ! Polarization
     real(r_kind)  :: wave4    ! WaveNumber
     real(r_kind)  :: varch4   ! variance for clear radiance
     real(r_kind)  :: tlap4    ! mean lapse rate (fixed from input file)
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
     real(r_kind),allocatable,dimension( : ) :: diagbuf     ! diagnostics
     real(r_kind),allocatable,dimension(:,:) :: diagbufex   ! extra diagnostics by channel
     real(r_kind),allocatable,dimension(:,:) :: diagbufchan ! channel information



     type(ChannelInfo), pointer :: chInfo(:) => null()
     type(ChannelData), pointer :: chData(:) => null()
     type(RadData),     pointer :: rad     => null()


     info => self%oInfo
!     if(associated(self%oInfo))then
!        print*,'Ja associado!'
!        stop
!     endif
     if (.not.associated(info))then    
        !------------------------------------------!
        ! Initialize some global variables
        allocate(self%nType)
        self%nType = 0
        
        allocate(self%nObs)
        self%nObs = 0
   
        allocate(self%MaxChanl)
        self%MaxChanl = 0
   
        self%impact = .false.
   
        self%udef   = udef
        !------------------------------------------!
     endif     
     lu  = 100

     if(present(IsisList))then
        nFiles = size(IsisList)
     else
        nFiles = 1
     endif

     OpenFiles: do iFile = 1, nFiles
        FileName=trim(FileNameMask)

        if(present(IsisList))then
           myName = trim(adjustl(IsisList(iFile)))
           !print*,'myName is:', trim(myName), iFile, nFiles, isisList(iFile)
           call str_template(strg=FileName,label=myName)
        endif
        
        inquire(File=trim(Filename), exist=existe)

        if( .not. existe)then
           write(*,'(A,1x,A)')'File not found:',trim(FileName)
           if (nFiles .eq. 1)then
              iret = -1
              return
           else
              cycle
           endif
        endif
        

        OPEN ( UNIT   = lu,            &
               FILE   = trim(FileName),&
               STATUS = 'OLD',         &
               IOSTAT = ios,           &
               CONVERT= 'BIG_ENDIAN',  &
               ACCESS = 'SEQUENTIAL',  &
               FORM   = 'UNFORMATTED')
        if(ios.ne.0) then
           print*,'error to open file',trim(FileName)
           iret = -1
           return
        endif

        read(lu,err=997) isis, dplat, obstype, jiter, nchanl, npred, idate, ireal, ipchan, iextra, jextra
!        write(*,*) isis, dplat, obstype, jiter, nchanl, npred, idate, ireal, ipchan, iextra, jextra

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
         ! Read Channel informations

         allocate(ChInfo(nchanl))

         if(nchanl .gt. self%MaxChanl) self%MaxChanl = nchanl
         
         do i = 1, nchanl
            read(lu) freq4, pol4, wave4, varch4, tlap4,iuse_rad, nuchan, ich

            ChInfo(i)%freq   = freq4
            ChInfo(i)%pol    = pol4
            ChInfo(i)%wave   = wave4
            ChInfo(i)%varch  = varch4
            ChInfo(i)%tlap   = tlap4
            ChInfo(i)%iuse   = iuse_rad
            ChInfo(i)%nuchan = nuchan
            ChInfo(i)%ich    = ich

         end do


        ! Read observation data

        allocate(diagbuf(ireal))
!        allocate(diagbufchan(ipchan+npred+1,nchanl))
        allocate(diagbufchan(ipchan+npred+2,nchanl))
        if(iextra > 0) allocate(diagbufex(iextra,jextra))


        ReadSatData: do
        
           if ( iextra > 0 )then
              read(lu, err=998,end=110)diagbuf, diagbufchan, diagbufex
           else
              read(lu, err=998,end=110)diagbuf, diagbufchan
           endif
           
           allocate(rad)

           ! info
           rad%ObsType= trim(obstype)
           rad%idplat = trim(dplat)
           rad%nchanl = nchanl

           ! Location
           rad%lat    = diagbuf( 1)     ! observation latitude (degrees)
           rad%lon    = diagbuf( 2)     ! observation longitude (degrees)
           rad%elev   = diagbuf( 3)     ! model (guess) elevation at observation location 
           rad%time   = diagbuf( 4)     ! observation time (hours relative to analysis time)

           ! sensor/sat info
           rad%iscanp = diagbuf( 5)     ! sensor scan position 
           rad%zasat  = diagbuf( 6)     ! satellite zenith angle (degrees)
           rad%ilazi  = diagbuf( 7)     ! satellite azimuth angle (degrees)
           rad%pangs  = diagbuf( 8)     ! solar zenith angle (degrees)
           rad%isazi  = diagbuf( 9)     ! solar azimuth angle (degrees)
           rad%sgagl  = diagbuf(10)     ! sun glint angle (degrees) (sgagl)
 
           ! surface parameters
           rad%sfcwc  = diagbuf(11)     ! fractional coverage by water
           rad%sfclc  = diagbuf(12)     ! fractional coverage by land
           rad%sfcic  = diagbuf(13)     ! fractional coverage by ice
           rad%sfcsc  = diagbuf(14)     ! fractional coverage by snow

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

           ! pointer can be allocated every time
           allocate(chData(nchanl))
           do i = 1, nchanl

              chData(i)%tb_obs   = diagbufchan(1,i)   ! observed brightness temperature (K)
              chData(i)%omf      = diagbufchan(2,i)   ! observed - simulated Tb with bias corrrection (K)
              chData(i)%omf_nobc = diagbufchan(3,i)   ! observed - simulated Tb with no bias correction (K)
              chData(i)%errinv   = diagbufchan(4,i)   ! inverse observation error

              if(diagbufchan(4,i) > rtiny)then
                 chData(i)%oer  = one/diagbufchan(4,i) 
              else
                 chData(i)%oer  = udef 
              endif

              chData(i)%idqc   = diagbufchan(5,i)   ! quality control mark or event indicator
              chData(i)%emiss  = diagbufchan(6,i)   ! surface emissivity
              chData(i)%tlach  = diagbufchan(7,i)   ! stability index
              chData(i)%ts     = diagbufchan(8,i)   ! d(Tb)/d(Ts)

              allocate(chData(i)%predterms(npred+2))
              do j = 1, npred + 2
                 chData(i)%predterms(j) = diagbufchan(ipchan+j,i) ! Tb bias correction terms (K)
              enddo

           enddo

           if (lwrite_peakwt)then

              do i = 1, nchanl
                 allocate(chData(i)%weigthmax)
                 chData(i)%weigthmax = diagbufex(1,i) ! press. at max of weighting fn (mb)
              enddo

              if(trim(obstype) == 'goes_img')then
                 do i = 1, nchanl
                    allocate(chData(i)%tb_obs_sdv)
                    chData(i)%tb_obs_sdv = diagbufex(2,i)
                 enddo
              endif

           else if (trim(obstype) == 'goes_img' .and. .not. lwrite_peakwt)then
           
              do i = 1, nchanl
                 allocate(chData(i)%tb_obs_sdv)
                 chData(i)%tb_obs_sdv = diagbufex(1,i)
              enddo

           endif

           rad%chInfo => chInfo
           rad%chData => chData

           !
           ! insert data to conv structure
           !

           call insert(info, trim(ObsType), rad, nchanl, isNewType, idate)

           if ( isNewType ) self%nType = self%nType + 1


        enddo ReadSatData

110     continue     
        close(lu)


        deallocate(diagbuf)
        deallocate(diagbufchan)
        if(iextra > 0) deallocate(diagbufex)

     enddo OpenFiles
     
     self%oInfo => info%First

     iret = 0
     return

997  iret = -95
     return

998  iret = -96
     return

  end function
  function Open__(self, File_FGS, File_ANL, IsisList) result(iret)
     class(rDiag)                     :: self
     character(len=*),           intent(in   ) :: File_FGS
     character(len=*),           intent(in   ) :: File_ANL
     Character(len=*), optional, intent(in   ) :: IsisList(:)
     Integer                                   :: iret


     type(rDiag)             :: file1
     type(ObsInfo), pointer  :: info1 => null()
     type(SatPlat), pointer  :: oSat1 => null()
     type(RadData), pointer  :: oData1 => null()

     type(rDiag)             :: file2
     type(ObsInfo), pointer  :: info2 => null()
     type(SatPlat), pointer  :: oSat2 => null()
     type(RadData), pointer  :: oData2 => null()

     real, pointer :: oma => null()
     real, pointer :: omf => null()
     real, pointer :: err => null()

     
     character(len=20) :: isis
     integer    :: ierr
     integer    :: k

     iret = 0

     if(present(IsisList))then
        ierr = file1%open(File_FGS, IsisList)
     else
        ierr = file1%open(File_FGS)
     endif
     if(ierr.ne.0)then
        print*,'error on file1:',trim(File_FGS), ierr
        iret = ierr
        return
     endif

     info1 => file1%oInfo%First     
     info1%impact = .true. 
     do while(associated(info1))
        oSat1 => info1%oSat%First
        do while(associated(oSat1))
           isis  = trim(info1%sensor)//"_"//trim(oSat1%idplat)
           ierr  = file2%open(File_ANL, [isis])
           if(ierr.ne.0)then
              print*,'error on file2:',trim(File_ANL),trim(isis), ierr
              iret = ierr
              return
           endif

           info2 => file2%oInfo%First
           oSat2 => info2%oSat%First

           oData1 => oSat1%oData%First
           oData2 => oSat2%oData%First
           do while(associated(oData1))
              
              do k=1,info1%nChanl

                 allocate(oData1%chData(k)%oma)
                 allocate(oData1%chData(k)%oma_nobc)
                 allocate(oData1%chData(k)%imp)
                 allocate(oData1%chData(k)%dfs)

                 oData1%chData(k)%oma      = oData2%chData(k)%omf
                 oData1%chData(k)%oma_nobc = oData2%chData(k)%omf_nobc
                 oData1%chData(k)%oer      = oData2%chData(k)%oer

                 omf => oData1%chData(k)%omf
                 oma => oData1%chData(k)%oma
                 err => oData1%chData(k)%oer

                 if(err .ne. udef .and. err .lt. 10.0)then
                    oData1%chData(k)%imp = (oma**2 - omf**2) / err
                    oData1%chData(k)%dfs = ( ( oma - omf ) * (omf) )  / err
                 else
                    oData1%chData(k)%imp = udef
                    oData1%chData(k)%dfs = udef
                 endif
                 
              enddo

              oData1 => oData1%next
              oData2 => oData2%next
           enddo
           
           ierr = file2%close( )
           if(ierr.ne.0)then
              write(*,'(A18,1x,A,1x,A,1x,I4)')'error close file2:',trim(File_ANL),trim(isis), ierr
              iret = ierr
              return
           endif

           oSat1 => oSat1%next
           
        enddo

        info1 => info1%next
     enddo

     ! obtain some statistics
     iret = file1%calcStat()

     ! assign to self pointer
     self%oInfo => file1%oInfo
     self%nType => file1%nType
     self%nObs => file1%nObs
     self%MaxChanl => file1%MaxChanl
     self%udef = file1%udef

!     ierr = file2%close( )

  end function



  function close_(self) result(iret)
     class(rDiag) :: self
     integer     :: iret

      iret = 0
      call deleteObsInfo(self%oInfo)
      nullify(self%oInfo)
      self%nType = -1
      self%nObs  = -1
      
  end function



  subroutine init_(self, oType, idate, nchanl, oData)

     type(ObsInfo), pointer, intent(inout) :: self
     character(len=*),       intent(in   ) :: oType
     integer,                intent(in   ) :: idate ! synoptic year/month/day
     integer,                intent(in   ) :: nChanl
     type(RadData), pointer, intent(in   ) :: oData

     integer :: iret, istat

     istat = 0

     !
     !
     ! Self
     !  └── oSat
     !        └── oData
     !
     
     !--------------------------------!
     ! Assingn Self information 

     allocate(self, stat = iret)
     istat = istat + iret

     self%Sensor = trim(otype)
     self%nChanl = nChanl
     self%nSatID = 1
     self%nobs   = 1
     self%date   = idate
     self%ymd    = int(idate/100)
     self%hms    = mod(idate,100) * 10000  

     self%First  => self
     nullify(self%Next)
     !--------------------------------!

     !--------------------------------!
     ! Assingn oSat information
     allocate(self%oSat, stat=iret)
     istat = istat + iret

     self%oSat%idplat = oData%idplat
     self%oSat%nobs   = 1
!     self%oSat%imp    = udef
!     self%oSat%dfs    = udef

     self%oSat%First  => self%oSat
     nullify(self%oSat%Next)
     !--------------------------------!

     !--------------------------------!
     ! Assign oData infomation

     self%oSat%oData  => oData
     self%oSat%oData%First => self%oSat%oData
     nullify(self%oSat%oData%Next)

     if (istat .ne. 0 ) then 
        print*,'Problem to init ...'
        stop
     endif
     return
  end subroutine

  function IsEmpty(self) result(answer)
     type(ObsInfo), pointer, intent(in) :: self
     logical :: answer
     
     answer = .not.associated(self)

  end function

  recursive subroutine insert(self, oType, odata, nChanl, isNewType, idate)

    type(ObsInfo), pointer, intent(inout) :: self
    character(len=*),       intent(in   ) :: oType
    type(RadData), pointer, intent(in   ) :: odata
    integer,                intent(in   ) :: nChanl
    logical, optional,      intent(  out) :: isNewType
    integer, optional,      intent(in   ) :: idate ! synoptic year/month/day

    integer                :: date

    type(ObsInfo), pointer :: NewType   => null()
    type(ObsInfo), pointer :: Find      => null()
    type(ObsInfo), pointer :: FirstType => null()
    type(SatPlat), pointer :: oSat      => null()

    integer :: iret

    if(present(isNewType)) isNewType = .FALSE.

    if(present(idate))then
       date = idate
    else
       date = 0
    endif

    !
    ! Verify if self is null
    !

    if(IsEmpty(self)) then
       !
       ! Only at First time
       !
       call init_(                       &
                  self    = self,        &
                  oType   = trim(oType), &
                  idate   = date,        & 
                  nChanl  = nChanl,      &
                  oData   = oData        &
                 )

       if(present(isNewType)) isNewType = .TRUE.
       return

    endif
    
    ! If not empty insert data at a existing pointer

    if(trim(self%Sensor).eq.trim(oType))then
       !
       ! Insert a new observation point
       ! in an existing variable
       !

       self%nobs = self%nobs + 1    

       !
       ! Organize data by Sattelite plataform Id
       !

       ! verify if current pointer have same SatId
       if(self%oSat%idplat .eq. oData%idplat)then

!          allocate(self%oSat%oData%next)

          self%oSat%oData%next => oData
          self%oSat%oData%next%First  => self%oSat%oData%First

          self%oSat%oData      => self%oSat%oData%next

          nullify(self%oSat%oData%next)

          self%oSat%nobs       = self%oSat%nobs + 1
          
       else

          ! find by required Sattelite Id
          oSat => self%oSat%First
          do while(associated(oSat))
            if(oData%idplat .eq. oSat%idplat)exit
!            self%oSat => oSat
            oSat      => oSat%Next
          enddo
   
          if(associated(oSat))then

!             allocate(oSat%oData%next)

             oSat%oData%next => oData
             oSat%oData%next%First => self%oSat%oData%First
             
             oSat%oData      => oSat%oData%next
             nullify(oSat%oData%next)

             oSat%nobs       = oSat%nobs + 1

          else
   
             allocate(oSat, stat=iret)
             oSat%idplat     = oData%idplat
             oSat%nobs       = 1

!             allocate(oSat%oData)
             oSat%oData       => oData
             oSat%oData%First => oSat%oData

             nullify(oSat%oData%next)
   
             oSat%First      => self%oSat%First
             self%oSat%next  => oSat
             self%oSat       => self%oSat%Next
             nullify(self%oSat%next)

             self%nSatId     = self%nSatId + 1
          endif
       endif

     else ! Insert a new observatoion Type (Sensor)

        !
        ! Return to first Sensor
        !

        Find => self%First
        FirstType => self%First

        !
        ! Find by observation type (Sensor)
        ! in the list

        do while(associated(Find))
           if(trim(Find%Sensor) .eq. trim(oType))then
              call insert(Find, oType, oData, nChanl)
              self => Find
              return
           endif
!           self => Find
           Find => Find%Next
        enddo

        !
        ! if not found
        ! create a NewVariable
        !

        allocate(NewType)
        nullify(NewType%Next)
        call init_(                      &
                   self   = NewType,     &
                   oType  = trim(oType), &
                   idate  = date,        &
                   nChanl = nChanl,      &
                   oData  = oData        &
                  )

        NewType%First => FirstType
        self%Next     => NewType
        self          => self%Next

        if(present(isNewType)) isNewType = .TRUE.

     endif


    return
  end subroutine insert


  function CalcStat_(self) result(iret)
     class(rDiag), intent(inout) :: self
     integer                    :: iret


     type(ObsInfo), pointer :: oType => null()
     type(SatPlat), pointer :: oSat  => null()
     type(RadData), pointer :: oData => null()
     integer                :: k
     
     self%impact = .true.
     oType => self%oInfo%First
     do while(associated(oType))

        allocate(oType%imp(0:oType%nChanl))
        oType%imp = 0.0
        allocate(oType%dfs(0:oType%nChanl))
        oType%dfs    = 0.0
        oType%Used   = 0
        otype%noUsed = 0
        oSat => oType%oSat%First
        do while(associated(oSat))

           allocate(oSat%imp(0:oType%nChanl))
           oSat%imp = 0.0
           allocate(oSat%dfs(0:oType%nChanl))
           oSat%dfs = 0.0
           oSat%used   = 0
           oSat%noused = 0
           oData => oSat%oData%First
           do while(associated(oData))

!            ! Account total observation impact ??!!
               do k = 1, oType%nchanl
                  if ( (oData%chData(k)%imp .ne. udef) .and. (oData%chInfo(k)%iuse .ge. 1))then
                     oSat%imp(k) = oSat%imp(k) + oData%chData(k)%imp
                     oSat%dfs(k) = oSat%dfs(k) + oData%chData(k)%dfs
                     oSat%used   = oSat%Used + 1
                  else
                     oSat%noUsed = oSat%noUsed + 1
                  endif              
               enddo

              oData => oData%next
           enddo

           oSat%imp(0) = sum(oSat%imp(1:oType%nChanl))
           oSat%dfs(0) = sum(oSat%dfs(1:oType%nChanl))

           do k = 1, oType%nChanl
              oType%imp(k) = oType%imp(k) + oSat%imp(k)
              oType%dfs(k) = oType%dfs(k) + oSat%dfs(k)
           enddo

           oType%Used   = oType%Used + oSat%Used
           oType%noUsed = oType%noUsed + oSat%noUsed

           oSat => oSat%Next
        enddo

        oType%imp(0)  = sum(oType%imp(1:oType%nChanl))
        oType%dfs(0)  = sum(oType%dfs(1:oType%nChanl))

        ! make fractional observation impacts
!        do k = 1, oType%nChanl
!           if (oType%imp(0) .ne. 0)oType%imp(k)  = oType%imp(k)  / oType%imp(0)
!           if (oType%dfs(0) .ne. 0)oType%dfs(k)  = oType%dfs(k)  / oType%dfs(0)
!        enddo

        oType => oType%Next
     enddo

     iret = 0

     return

  end function

  !EOC
  !-------------------------------------------------------------------!

  function Sumarize_(self) result(iret)
     class(rDiag), intent(in) :: self
     integer                :: iret

     type(ObsInfo), pointer :: oType => null()
     type(SatPlat),   pointer :: oSat  => null()
     integer :: total
     real :: pused, pnoused


     iret = 0
     write(*,'(A)')'-------------- Impact Info ------------------'
        print*,''
     oType => self%oInfo%First
     do while(associated(oType))
!        write(*,'(1x,A10,4(1x,F16.3))') trim(oType%Sensor), oType%imp(0), oType%dfs(0), &
!                                       oType%imp(0)/oType%Used, oType%dfs(0)/oType%Used
        write(*,'(1x,A10,A8,4(1x,A16))') trim(oType%Sensor),'satId','Impact','dfs','ave(imp)','ave(dfs)'

!        write(*,'(11x,A10,4(1x,A16))')'satId','Impact','dfs','ave(imp)','ave(dfs)' 
        oSat => oType%oSat%First
        do while(associated(oSat))
           if(associated(oSat%Next))then
              write(*,'(8x,A3,A10,4(1x,F16.3))')'├──',trim(oSat%idplat), oSat%imp(0), oSat%dfs(0), &
                                                      oSat%imp(0)/oSat%used,oSat%dfs(0)/oSat%used
           else
              write(*,'(8x,A3,A10,4(1x,F16.3))')'└──',trim(oSat%idplat), oSat%imp(0), oSat%dfs(0), &
                                                      oSat%imp(0)/oSat%used,oSat%dfs(0)/oSat%used
                                                    

           endif
           oSat => oSat%Next
        enddo

        print*,''
        write(*,'(19x,4(1x,F16.3))') oType%imp(0), oType%dfs(0), &
                              oType%imp(0)/oType%Used, oType%dfs(0)/oType%Used

        print*,''
        oType => oType%Next
     enddo

     write(*,'(A)')'-------------- Counting Info ------------------'
    ! Total
     oType => self%oInfo%First
     do while(associated(oType))
        total = oType%nObs*oType%nChanl
        write(*,'(1x,A10,3(I9))') trim(oType%Sensor)!, oType%nObs, oType%nChanl, total
        write(*,'(8x,A3,A10,3(1x,A16),2(1x,A8))')'│','id','nObs','used','not used', '% used','% not used'

        oSat => oType%oSat%First
        do while(associated(oSat))
           total   = oSat%nObs*oType%nChanl
           pused   = (oSat%Used/real(total,4))*100.0
           pnoused = (oSat%noUsed/real(total,4))*100.0
           if(associated(oSat%Next))then
              write(*,'(8x,A3,A10,3(1x,I16.3),2(1x,F8.2))')'├──',trim(oSat%idplat), oSat%nObs*oType%nChanl, oSat%Used, &
                                                                   oSat%noUsed, pused, pnoused
           else
              write(*,'(8x,A3,A10,3(1x,I16.3),2(1x,F8.2))')'└──',trim(oSat%idplat), oSat%nObs*oType%nChanl, oSat%Used, &
                                                                   oSat%noUsed, pused, pnoused

           endif
           oSat => oSat%Next
        enddo
        
        print*,''
        oType => oType%Next
     enddo


  end function

  function GetImpact_(self, imp)result(iret)
     class(rDiag),       intent(inout) :: self
     real, allocatable, intent(inout) :: imp(:,:)
     integer :: iret

     type(obsInfo), pointer :: oType => null()
     integer :: i, j

     iret = 0
     
     if(.not.Self%impact)then
        iret = self%CalcStat( )
     endif

     allocate(imp(self%nType,0:self%MaxChanl))
     oType => self%oInfo%First
     do i=1,self%nType
        do j = 0, oType%nChanl
           imp(i,j) = oType%imp(j)
        enddo
        oType => oType%Next
     enddo
  end function

  subroutine GetObsInfo_(self, Sensor, SatId, ObsTable, istat)
     class(rDiag),              intent(in   ) :: Self
     character(len=*),          intent(in   ) :: Sensor
     character(len=*),          intent(in   ) :: SatId
     real(r_kind), allocatable, intent(inout) :: ObsTable(:,:)
     integer, optional,         intent(  out) :: istat


     type(ObsInfo), pointer :: oType => null()
     type(SatPlat), pointer :: oSat  => null()
     type(RadData), pointer :: oData => null()
     character(len=10) :: oT1, oT2
     character(len=10) :: oS1, oS2
     
     integer :: i, k
     integer :: TotalObs
     integer :: ierr

     if(present(istat)) istat = 0

     oT1 = trim(adjustl(Sensor))
     oS1 = trim(adjustl(SatId))
     !write(*,'(4(1x,A))')'Sensor:', trim(oT1),'SatPlat:', trim(oS1)

     oType => Self%oInfo%First
     do while(associated(oType))
        oT2 = trim(adjustl(oType%Sensor))
        if( oT1 .eq. oT2 )then
           oSat => oType%oSat%First
           do while(associated(oSat))
              oS2 = trim(adjustl(oSat%idplat))
              if( oS1 .eq. oS2 )then
              oData => oSat%oData%First
              TotalObs = oSat%nObs * otype%nChanl
              if(allocated(ObsTable)) deallocate(ObsTable)
              if(Self%impact)then
                 allocate(ObsTable(TotalObs,17), stat = ierr)
              else
                 allocate(ObsTable(TotalObs,13), stat = ierr)
              endif
              if(ierr .gt. 0)then
                 if(present(istat)) istat = ierr
                 return
              endif

              i=1
              do while(associated(oData))

                 do k = 1,oType%nChanl
                    ObsTable(i, 1) = oData%lat
                    ObsTable(i, 2) = oData%lon
                    ObsTable(i, 3) = oData%elev
                    ObsTable(i, 4) = oData%chInfo(k)%nuchan
                    ObsTable(i, 5) = oData%time
                    ObsTable(i, 6) = oData%chInfo(k)%iuse
                    ObsTable(i, 7) = oData%chData(k)%idqc     ! quality control mark or event indicator
                    ObsTable(i, 8) = oData%chData(k)%errinv   ! inverse observation error
                    ObsTable(i, 9) = oData%chData(k)%oer      ! observation error
                    ObsTable(i,10) = oData%chData(k)%tb_obs   ! observed brightness temperature (K)
                    ObsTable(i,11) = oData%chData(k)%omf      ! observed - simulated Tb with bias corrrection (K)
                    ObsTable(i,12) = oData%chData(k)%omf_nobc ! observed - simulated Tb with no bias corrrection (K)
                    ObsTable(i,13) = oData%chData(k)%emiss    ! surface emissivity
                    if (Self%impact)then
                       ObsTable(i,14) = oData%chData(k)%oma      ! observed - analised Tb with bias corrrection (K)
                       ObsTable(i,15) = oData%chData(k)%oma_nobc ! observed - analised Tb with no bias corrrection (K)
                       ObsTable(i,16) = oData%chData(k)%imp      ! observation impact
                       ObsTable(i,17) = oData%chData(k)%dfs      ! degree of freedom for signal
                    endif

                    i = i + 1
                 enddo
                 oData => oData%Next
              enddo
              endif
              oSat => oSat%Next
           enddo
        endif
        oType => oType%Next
     enddo

     if(.not.allocated(ObsTable).and.present(istat))then
        istat = -1
        return
     endif

  end subroutine


  function GetTotalObs_(self)result(nobs)
     class(rDiag)          :: self
     integer             :: nobs

     type(ObsInfo), pointer  :: oType => null()


     nobs = 0
     oType => self%oInfo%First
     do while(associated(oType))
        nobs = nobs + oType%nobs
        oType => oType%Next
     enddo

  end function

   function GObt_(self) result(iret)
     class(rDiag)      :: self
!     character(len=*) :: Sensor
     integer          :: iret

     type(ObsInfo), pointer  :: oType => null()
     type(SatPlat), pointer  :: oSat => null()
     character(len=10)       :: v2

!     v1 = trim(adjustl(Sensor))
     oType => self%oInfo%First
     !print*,'GObt_', associated(oType)
     do while(associated(oType))
        v2 = trim(adjustl(oType%Sensor))
!        if(v1 .eq. v2)then
           write(*,'(1x,A,I4,I10)')'Number of Satellite: ',oType%nSatId, oType%nobs
           oSat => oType%oSat%First
           do while(associated(oSat))
              write(*,'(5x,2(A,1x),I10)') trim(v2), trim(oSat%idplat), oSat%nObs
              oSat => oSat%next
           enddo
!        endif

        oType => oType%Next
     enddo

     iret = 0


  end function

  function GetDate_(self) result (idate)
     class(rDiag)   :: self
     integer       :: idate

     idate = self%oInfo%date
     
  endfunction


  function GetNObs_(self,Sensor)result(nobs)
     class(rDiag)         :: self
     character(len=*)    :: Sensor
     integer             :: nobs

     type(ObsInfo), pointer  :: oType => null()
     character(len=10) :: v1, v2

     v1   = trim(adjustl(Sensor))
     nobs = 0

     oType => self%oInfo%First
     do while(associated(oType))
        v2 = trim(adjustl(oType%Sensor))

        if(v1 .eq. v2) nobs = nobs + oType%nobs

        oType => oType%Next
     enddo

  end function

  subroutine GetFirstSensor_(self, First)
     class(rDiag)            :: self
     type(ObsInfo), pointer, intent(out) :: First => null()

     First => self%oInfo%First

  end subroutine

  function GetSensors_(self, Sensor) result(iret)
     class(rDiag) :: self
     type(ObsInfo), pointer :: oType => null()
     character(len=*),allocatable, intent(inout) :: Sensor(:)
     integer :: iret
     integer :: i

     allocate(Sensor(self%nType))
     call self%getFirstSensor(oType)
     do i=1,self%nType
        Sensor(i) = oType%sensor
        oType => oType%Next
     enddo
     iret = 0
     return
  end function

!    subroutine insertSat_(self, oData)
!       type(SatPlat),  pointer, intent(inout) :: self
!       type(RadSat), pointer, intent(in   ) :: oData
!
!       type(SatPlat),   pointer :: oSat => null()
!       type(RadData), pointer :: obs  => null()
!
!
!       if(.not. associated(self))then
!
!          allocate(oSat)
!          oSat%idplat = oData%idplat
!          oSat%nObs   = 1
!          oSat%imp    = udef
!          oSat%dfs    = udef
!          oSat%oData  => oData
!          oSat%First  => oSat
!
!          nullify(oSat%next)
!          nullify(oSat%oData%next)
!
!          self%oSat%Next => oSat
!          self%oSat => self%oSat%next
!
!       elseif(self%idplat .eq. oData%idplat)then
! 
!          self%nobs = self%nobs + 1
!
!          obs => oData
!          obs%First => self%oData%First
!
!          self%oData%next => obs
!          self%oData => self%oData%next
!
!          nullify(self%oData%next)
!          
!
!       else
!
!         call insertSat_
!
!      endif 
!
!
!    end subroutine

!    subroutine insertData_(self, oData)
!       type(RadData), pointer, intent(inout) :: self
!       type(RadData), pointer, intent(in   ) :: oData

    subroutine DeleteRadData(self)
       type(RadData), pointer, intent(inout) :: self
       
       type(RadData), pointer :: current => null()
       type(RadData), pointer :: next => null()

       type(ChannelData), pointer :: chData(:) => null()
       integer :: i
       if (.not. associated(self%first)) return

       current => self%first
       next => current%next
       do
           if(associated(current%imp)) deallocate(current%imp)
           if(associated(current%dfs)) deallocate(current%dfs)
           if(associated(current%cls)) deallocate(current%cls)
           if(associated(current%cldp)) deallocate(current%cldp)
           if(associated(current%clw)) deallocate(current%clw)
           if(associated(current%tpwc)) deallocate(current%tpwc)
           nullify(current%chInfo)

           chData => current%ChData
           do i=1, current%nchanl
              if(allocated(chData(i)%predterms))deallocate(chData(i)%predterms)
              if(associated(chData(i)%oma))nullify(chData(i)%oma)
              if(associated(chData(i)%oma_nobc))nullify(chData(i)%oma_nobc)
              if(associated(chData(i)%imp))nullify(chData(i)%imp)
              if(associated(chData(i)%dfs))nullify(chData(i)%dfs)
              if(associated(chData(i)%weigthmax))nullify(chData(i)%weigthmax)
              if(associated(chData(i)%tb_obs_sdv))nullify(chData(i)%tb_obs_sdv)
           enddo
           deallocate(current%chData)

           deallocate(current)
           if (.not. associated(next)) exit
           current => next
           next => current%next
       enddo

    end subroutine

    subroutine DeleteSatId(self)
       type(SatPlat), intent(inout) :: self
       
       type(SatPlat), pointer :: current => null()
       type(SatPlat), pointer :: next => null()

       if (.not. associated(self%first)) return

       current => self%first
       next => current%next
       do
           call DeleteRadData(Current%oData)
           deallocate(current)
           if (.not. associated(next)) exit
           current => next
           next => current%next
       enddo
    end subroutine

    subroutine DeleteObsInfo(self)
       type(ObsInfo), pointer, intent(inout) :: self
       
       type(ObsInfo), pointer :: current => null()
       type(ObsInfo), pointer :: next => null()

       if (.not. associated(self%first)) return

       current => self%first
       next => current%next
       
       do
           if(allocated(current%imp)) deallocate(current%imp)
           if(allocated(current%dfs)) deallocate(current%dfs)
           call DeleteSatId(current%oSat)
           deallocate(current)
           if (.not. associated(next)) exit
           current => next
           next => current%next
       enddo
       
    end subroutine

    subroutine getSensorInfo_(self,sensor,info, iret)
       class(rDiag),           intent(in   ) :: self
       character(len=*),       intent(in   ) :: sensor
       type(ObsInfo), pointer, intent(  out) :: info
       integer,                intent(  out) :: iret

       info => self%oInfo%First
       do while(associated(info))
          if (trim(sensor).eq.trim(info%sensor))then
             iret = 0
             return
          endif
          info => info%next
       enddo
       iret = -1
       return
    end subroutine

    subroutine getSatPlataform_(self, sensor, idplat, oSat, iret)
       class(rDiag),           intent(in   ) :: self
       character(len=*),       intent(in   ) :: sensor
       character(len=*),       intent(in   ) :: idplat
       type(SatPlat), pointer, intent(  out) :: oSat
       integer,                intent(  out) :: iret

       type(ObsInfo), pointer :: info => null()

       info => self%oInfo%First
       do while(associated(info))
          if (trim(sensor).eq.trim(info%sensor))then
             oSat => info%oSat%first
             do while(associated(oSat))
                if (trim(idplat) .eq. trim(oSat%idplat))then
                   iret = 0
                   return
                endif
                oSat => oSat%next
             enddo             
          endif
          info => info%next
       enddo
       iret = -1
       return
    end subroutine


 end module ReadDiagModRad

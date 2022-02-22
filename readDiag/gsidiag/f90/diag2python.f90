module Diag2Python
   use iso_c_binding
   use ReadDiagMod, only: conv=>Diag, CObsInfo => ObsInfo, ObsType, node
   use ReadDiagModRad, only : rad=>rDiag, RObsInfo => ObsInfo, SatPlat
   use m_string, only: str_template
   Implicit None
   Private

   Public :: open
   Public :: close
   Public :: GetObs
   Public :: getVarTypes
!   Public :: GetVarNames
   Public :: getObsVarInfo
   Public :: GetVarInfo
   Public :: GetnVars
   public :: getFileType
   public :: getUndef
!!   Public :: Gobt

   character(len=*),parameter :: myname = 'diag2python'

   Real, Public, Allocatable :: Array1D(    :)
   Real, Public, Allocatable :: Array2D(  :,:)
   Real, Public, Allocatable :: Array3D(:,:,:)

   Character(len=32), Public, Allocatable :: CharArray1D(  :)
   Character(len=32), Public, Allocatable :: CharArray2D(:,:)

   type acc
      integer               :: FNumber
      character(len=512)    :: fileDiag
      character(len=512)    :: fileDiagAnl
      integer               :: fileType
      integer               :: iret
      class(*), allocatable :: data
      type(acc), pointer    :: next => null()
   end type

   type files
      integer             :: fCount
      type(acc),  pointer :: tail => null()
      type(acc),  pointer :: root => null()
   end type files
   type(files) :: diagFile


   contains

   function open(fileDiag, fileDiagAnl, isis) result(FNumber)

      Character(len=*), intent(in) :: fileDiag
      Character(len=*), intent(in) :: fileDiagAnl
      character,        intent(in) :: isis(:,:) ! this is a trick to process arrays of strings 
                                                ! from python using f2py
                                                ! 1st dimension is the string size
                                                ! 2nd dimension is the array size
      Integer                      :: FNumber

      integer            :: bufr0, bufr1
      logical            :: existe
      integer            :: FileCount
      integer            :: iret, i
      logical            :: F2_existe
      character(len=1024):: N1, N2, N3
      integer            :: strSize, arrSize
      character(len=60), allocatable :: isisList(:)
      type(acc), pointer :: d => null()
      type(acc), pointer :: tmp => null()

      character(len=*), parameter :: myname_=myname//' :: open()'

      !process isis character array from python
      
      strSize = size(isis,1)
      arrSize = size(isis,2)
      !print*,strSIze,arrSize
      allocate(isisList(arrSize))
      do i=1,arrSize
         isisList(i) = transfer(isis(:,i),isisList(i)(1:strSIze))
      enddo
      !do i=1,arrSize
      !   print*,trim(isisList(i))
      !enddo
      !
      ! First open file
      !

      if(.not.associated(diagFile%root))then

         ! define data file type
   
         diagFile%fCount = 0

         allocate(diagFile%root)
         diagFile%tail => diagFile%root
         d => diagFile%tail
         
      else

         !
         ! Verify if file is already open
         !
         
         N1 = trim(adjustl(fileDiag))

         d => diagFile%root
         do while(associated(d))

            N2 = trim(adjustl(d%fileDiag))
            N3 = trim(adjustl(d%fileDiagAnl))

            if(trim(N1).eq.trim(N2).or.trim(N1).eq.trim(N3))then
               write(*,'(2(A,1x),A)')trim(myname_),'File already open:',trim(N1)
               FNumber = d%FNumber
               return
            endif

            tmp => d
            d   => d%next

         enddo

         !
         ! It's not open
         !
         allocate(tmp%next)
         d=> tmp%next

      endif
      call assignPointer(d, fileDiag, fileDiagAnl, isisList, iret)
      if(iret .eq. 0 )then
         diagFile%fCount = diagFile%fCount + 1

         d%FNumber     = diagFile%fCount
         d%fileDiag    = trim(adjustl(fileDiag))
         d%fileDiagAnl = trim(adjustl(fileDiagAnl))

         FNumber     = diagFile%fCount
      else
      
         FNumber = iret
         
      endif

   end function

   subroutine assignPointer(d, diagFile, diagFileAnl, isis, iret)

      type(acc), pointer, intent(inout) :: d
      character(len=*),   intent(in   ) :: diagFile
      character(len=*),   intent(in   ) :: diagFileAnl
      character(len=*),   intent(in   ) :: isis(:)
      integer,            intent(  out) :: iret

      integer :: bufr0, bufr1
      logical :: existe
      logical :: F2_existe
      character(len=512) :: fileName1, fileName2, myName

      iret      = 0
      F2_existe = (trim(diagFileAnl) .ne. 'None')

      !
      ! test if diag file if for conventional or radiance data
      ! Conventional diag file has 4 bytes at header
      ! Radiance diag file has 92 bytes at header
      !   OBS: we found a radiance file with 88 bytes,
      !        so if header is greater than 4 bytes, perhaps
      !        this file is for radiance data

      !----------------------------------------------------------------!
      ! if we have a isisList, so diagFile and diagFileAnl should have
      ! a mask %e inside that need be filled with isis name.
      ! this same operation is made inside radDiag module, but here we 
      ! should do this because we need verify what is the kind of file. 
      fileName1 = diagFile
      fileName2 = diagFileAnl
      if (isis(1)/='None')then
         myName    = trim(adjustl(Isis(1)))
         call str_template(strg=FileName1,label=myName)
         call str_template(strg=FileName2,label=myName)
      endif
      !----------------------------------------------------------------!

      inquire(File=Trim(FileName1),exist=existe)
      if(.not.existe)then
         write(*,'(2A)')'File not found:',trim(fileName1)
         iret = -1
         return
      endif
      Open(Unit    = 99,              &    
           File    = trim(fileName1), &
           access  = 'stream',        &
           status  = 'old',           &
           form    = 'unformatted',   &
           convert = 'big_endian'     &
           )

      read(99) bufr0
      close(99)

      if(trim(diagFileAnl) /= 'None')then
         inquire(File=Trim(fileName2),exist=F2_existe)
         if(.not.F2_existe)then
            write(*,'(2A)')'File not found:',trim(fileName2)
            iret = -2 
            return
         endif

         Open(Unit    = 99,              &    
              File    = trim(fileName2), &
              access  = 'stream',        &
              status  = 'old',           &
              form    = 'unformatted',   &
              convert = 'big_endian'     &
              )
   
         read(99) bufr1
         close(99)

         ! sanity check
         if (bufr0 .ne. bufr1)then
            write(*,*) 'Files data types differs! Abort ... '
            iret = -3
            return
         endif

      endif
      

      select case (bufr0)
         case(4) ! file is for conventional data
            allocate(conv::d%data)
         case(88:) ! file is for radiance date => !88, 92 <- found a 88 bytes
            allocate(rad::d%data)
         case default
            write(*,*)'Wrong data file type! Abort ... '
            write(*,*)'Neither conventional nor radiance diag file type!'
            iret = -3
            return
      end select

      if(F2_existe)then
         select type (ptr => d%data)
            type is (conv)
               d%iret = ptr%open(trim(diagFile),trim(diagFileAnl))
            type is (rad)
               if (isis(1).ne.'None')then
                  d%iret = ptr%open(trim(diagFile),trim(diagFileAnl), isisList=isis)
               else
                  d%iret = ptr%open(trim(diagFile),trim(diagFileAnl))
               endif
         end select
      else
         select type (ptr => d%data)
            type is (conv)
               d%iret = ptr%open(trim(diagFile))
            type is (rad)
               if(isis(1).ne.'None')then
                  d%iret = ptr%open(trim(diagFile),isisList=isis)
               else
                  d%iret = ptr%open(trim(diagFile))
               endif
         end select
      endif

      iret = d%iret

   end subroutine


   function close(FNumber) result(iret)
      Integer, intent(in) :: FNumber
      Integer             :: iret
      Type(acc), pointer  :: curr => null()
      Type(acc), pointer  :: prev => null()

      iret = 0

      prev => diagFile%root
      curr => diagFile%root%next

      if (prev%FNumber .eq. FNumber)then
         select type (ptr => prev%data)
            type is (conv)
               iret = ptr%close()
            type is (rad)
               iret = ptr%close()
         end select

         deallocate(prev)
         diagFile%root => curr
         return

      endif

      do while(associated(curr))

         if(curr%FNumber .eq. FNumber) then
            
            prev%next => curr%next

            select type (ptr => prev%data)
               type is (conv)
                  iret = ptr%close()
               type is (rad)
                  iret = ptr%close()
            end select

            deallocate(curr)

            exit
            
         endif

         prev => curr
         curr => curr%next
      enddo
   end function


   subroutine GetVarInfo(FNumber, VarName, nKx)
      integer,          intent(in   ) :: FNumber
      character(len=*), intent(in   ) :: VarName
      integer,          intent(  out) :: nKx

      type(CObsInfo), pointer :: ObsNow => null()
      type(ObsType), pointer :: oType => null()

      type(RObsInfo), pointer :: SensorNow => null()
      type(SatPlat), pointer :: oSat => null()

      type(acc), pointer :: d => null()

      character(len=10) :: v1, v2

      integer :: i

      !
      ! Release array2d if allocated
      !

      if(allocated(Array2D)) deallocate(Array2D)

      !
      ! Find by file opened
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo


      select type(ptr => d%data)
         type is (conv)

            !
            ! Get first variable
            !
      
            call ptr%GetFirstVar(ObsNow)
      
            !
            ! Find by VarName
            !
            v1 = trim(adjustl(VarName))
            do while(associated(ObsNow))
      
               v2 = trim(adjustl(ObsNow%VarName))
      
               !now find by ObsType (kx)
               if(v1 .eq. v2) then
      
                 oType => ObsNow%OT%FirstKX
                 nKx = ObsNow%nKx
                 allocate(Array2D(ObsNow%nKx,2))
                 do i=1,ObsNow%nKx
                    Array2D(i,1) = oType%kx
                    Array2D(i,2) = oType%nobs
                    oType => oType%nextKX
                 enddo
                
               endif
      
               ObsNow => ObsNow%NextVar
            enddo

         type is (rad)
            !
            ! Get first variable
            !
      
            call ptr%GetFirstSensor(SensorNow)
      
            !
            ! Find by VarName
            !
            v1 = trim(adjustl(VarName))
            do while(associated(SensorNow))
      
               v2 = trim(adjustl(SensorNow%Sensor))
      
               !now find by ObsType (kx)
               if(v1 .eq. v2) then
      
                 oSat => SensorNow%oSat%First
                 nKx = SensorNow%nSatID
                 allocate(Array1D(nKx))
                 allocate(CharArray1D(nKx))
                 do i = 1,nKx
                    CharArray1D(i) = oSat%idplat
                    Array1D(i)     = oSat%nobs * SensorNow%nChanl
                    oSat => oSat%Next
                 enddo
                
               endif
      
               SensorNow => SensorNow%Next
            enddo

      end select

   end subroutine

   function getnvars(FNumber) result(nVars)
      integer, intent(in   ) :: FNumber
      integer                :: nVars

      type(acc), pointer :: d => null()


      !
      ! Find by file opened
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      !
      ! Get number of variables
      !

      select type(ptr => d%data)
         type is (conv); nVars = ptr%nVars
         type is  (rad); nVars = ptr%nType
      end select

   end function

   subroutine getObsVarInfo(FNumber, nVars, vNames, nTypes)
      integer,                        intent(in   ) :: FNumber
      integer,                        intent(in   ) :: nVars
      character*15, dimension(nVars), intent(  out) :: vNames
      integer,      dimension(nVars), intent(  out) :: nTypes


      type(acc),      pointer :: d => null()
      type(CObsInfo), pointer :: CObsRoot => null()
      type(CObsInfo), pointer :: CtmpObs => null()
      type(RObsInfo), pointer :: RObsRoot => null()
      type(RObsInfo), pointer :: RtmpObs => null()
    

        integer :: i

      
      !
      ! Find by file opened
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo
      
      !
      ! sanity check
      !

      select type (ptr => d%data)

         type is (conv)
            !
            ! Get first variable
            !
            call ptr%GetFirstVar(CObsRoot)
            CtmpObs => CObsRoot
            do i = 1, nVars
               vNames(i) = trim(CtmpObs%VarName)
               nTypes(i) = cTmpObs%nKx
               CtmpObs   => CtmpObs%NextVar
            enddo
         type is (rad)
            call ptr%GetFirstSensor(RObsRoot)
            RtmpObs => RobsRoot
            do i = 1, nvars
               vNames(i) = trim(RtmpObs%Sensor)
               nTypes(i) = RtmpObs%nSatId
            enddo
         class default
            write(*,*)'File is not conventional nor radiance type'
            return
      end select



   end subroutine

   subroutine getVarTypes(FNumber, vName, nTypes, vTypes, svTypes)
      integer,                         intent(in   ) :: FNumber
      character*15,                    intent(in   ) :: vName
      integer,                         intent(in   ) :: nTypes
      integer,      dimension(nTypes), intent(  out) :: vTypes
      character*15, dimension(nTypes), intent(  out) :: svTypes

      integer :: i
      type(acc),      pointer :: d => null()
      
      type(CObsInfo), pointer :: CtmpObs => null()
      type(ObsType), pointer :: ObType => null()

      type(RObsInfo), pointer :: rTmpObs => null()
      type(satPlat), pointer :: oSat => null()

      !
      ! Find by file opened
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      select type (ptr => d%data)
         type is (conv)
            !
            ! Get first variable
            !
            call ptr%getFirstVar(cTmpObs)
            do while(associated(cTmpObs))
               if (trim(vName) .eq. trim(adjustl(cTmpObs%varName)))then
                  ObType => cTmpObs%OT%FirstKX
                  i=1
                  do while(associated(ObType))
                    vTypes(i)  = ObType%kx
                    svTypes(i) = ' ' 
                    i=i+1
                    ObType => ObType%nextKX
                  enddo
      
               endif
               CtmpObs     => CtmpObs%NextVar
            enddo
         type is (rad)
            !
            ! Get first plataform
            !
            call ptr%getFirstSensor(rTmpObs)
            do while(associated(rTmpObs))
               if (trim(vName) .eq. trim(adjustl(rTmpObs%sensor)))then
                  oSat => rTmpObs%oSat%First
                  i=1
                  do while(associated(oSat))
                    vTypes(i)  = i
                    svTypes(i) = trim(oSat%idplat)
                    i=i+1
                    oSat => oSat%next
                  enddo
      
               endif
               rTmpObs     => rTmpObs%Next
            enddo
            
      end select

   end subroutine


   subroutine GetVarNames(FNumber, nVars, VarNames)
      integer, intent(in) :: FNumber
      integer, intent(in) :: nVars
      character*4, dimension(nVars), intent(out) :: VarNames


      type(acc),      pointer :: d => null()
      type(CObsInfo), pointer :: CObsRoot => null()
      type(CObsInfo), pointer :: CtmpObs => null()
      type(RObsInfo), pointer :: RObsRoot => null()
      type(RObsInfo), pointer :: RtmpObs => null()

      integer :: i

      
      !
      ! Find by file opened
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo
      select type (ptr => d%data)
         type is (conv)

            !
            ! Get first variable
            !
            call ptr%GetFirstVar(CObsRoot)
            CtmpObs => CObsRoot
            do i = 1, nVars
               VarNames(i) = trim(CtmpObs%VarName)
               CtmpObs     => CtmpObs%NextVar
            enddo

         type is (rad)

            !
            ! Get first Sensor
            !
            call ptr%GetFirstSensor(RObsRoot)
            RtmpObs => RObsRoot
            do i = 1, nVars
               VarNames(i) = trim(RtmpObs%Sensor)
               RtmpObs     => RtmpObs%Next
            enddo

      end select

   end subroutine

   subroutine GetObs  (FNumber, oName, oType, oSatId, zlevs, n, NObs)
      integer,          intent(in   ) :: FNumber
      character(len=*), intent(in   ) :: oName
      integer,          intent(in   ) :: oType
      character(len=*), intent(in   ) :: oSatId 
      integer,          intent(in   ) :: n
      real,             intent(in   ) :: zlevs(n)
      integer,          intent(  out) :: NObs


      type(acc), pointer :: d => null()


      !
      ! Release array2d if allocated
      !

      if(allocated(Array2D)) deallocate(Array2D)

      !
      ! Find File Number
      !

      d => diagFile%root
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      if(.not.associated(d)) then
         print*, 'No file open ... ', FNumber
         return
      endif

      select type (ptr => d%data)
         type is (conv)
            Array2D = ptr%GetObsInfo(oName, oType, zlevs)
            nObs    = size(Array2D,1)
         type is (rad)
            call ptr%GetObsInfo(oName, oSatId, Array2D)
            nObs    = size(Array2D,1)
      end select 
  
   end subroutine
!   
!   subroutine GetObsRad(FNumber, Sensor, SatId, NObs)
!      integer,          intent(in   ) :: FNumber
!      character(len=*), intent(in   ) :: Sensor
!      character(len=*), intent(in   ) :: SatId
!      integer,          intent(  out) :: NObs
!
!      type(acc), pointer :: d => null()
!      integer :: ierr
!      
!      !
!      ! Release array2d if allocated
!      !
!
!      if(allocated(Array2D)) deallocate(Array2D)
!
!      !
!      ! Find File Number
!      !
!      d => diagFile%root
!      do while(associated(d))
!         if(FNumber.eq.d%FNumber) exit
!         d => d%next
!      enddo
!
!      if(.not.associated(d)) then
!         print*, 'No file open ... ', FNumber
!         return
!      endif
!      
!      call d%rad%GetObsInfo(Sensor, SatId, Array2D, ierr)
!      if(ierr .ne. 0)then
!         nObs = -1
!         write(*,*)'Error to get Sensor:', trim(Sensor), ' or SatPlat:', trim(SatId)
!         return
!      else
!         nObs = size(Array2D,1)
!      endif
!      return
!
!
!   end subroutine

   function getFileType(FNumber)result(fileType) 
      integer             :: FNumber
      integer             :: fileType

      type(acc), pointer :: f => null()

      f => diagFile%root
      do while(associated(f))
         if (f%FNumber .eq. FNumber)then
            select type (ptr => f%data)
               type is (conv)
                  fileType = 1
               type is (rad)
                  fileType = 2
            end select
            return
         endif
         f => f%next
      enddo
      write(*,*)'error: File number does not exist:', FNumber
      fileType = -1
   end function

   function getUndef(FNumber) result(undef)
      integer :: FNumber 
      real    :: undef

      type(acc), pointer :: f => null()

      f => diagFile%root
      do while(associated(f))
         if (f%FNumber .eq. FNumber)then
            select type (ptr => f%data)
               type is (conv)
                  undef = ptr%udef
               type is (rad)
                  undef = ptr%udef
            end select
            return
         endif
         f => f%next
      enddo

   end function

end module
